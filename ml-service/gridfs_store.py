"""MongoDB GridFS persistent artifact storage for ESS Sentinel Web 3.0.
Ensures durable storage of datasets, model bundles, screening results, and reports
across ephemeral container restarts and redeployments.
"""
import os
import io
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from bson import ObjectId

CHUNK_SIZE = 255 * 1024  # Standard 255 KB GridFS chunk size

def guess_type(filename):
    ext = Path(filename).suffix.lower()
    mapping = {
        '.csv': 'text/csv; charset=utf-8',
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.bin': 'application/octet-stream',
        '.joblib': 'application/octet-stream',
        '.json': 'application/json',
        '.zip': 'application/zip',
    }
    return mapping.get(ext, mimetypes.guess_type(filename)[0] or 'application/octet-stream')

class GridFSArtifactStore:
    def __init__(self, db, root=None):
        self.db = db
        self.root = Path(root).resolve() if root else None
        if self.root:
            self.root.mkdir(parents=True, exist_ok=True)
        self._is_mock = type(db).__module__.startswith('mongomock')
        if not self._is_mock:
            try:
                import gridfs
                self.bucket = gridfs.GridFSBucket(db)
            except Exception:
                self.bucket = None
        else:
            self.bucket = None

    def _ensure_indexes(self):
        """Ensure indexes on fs.files and fs.chunks for fast artifact lookups."""
        try:
            self.db['fs.files'].create_index([
                ('metadata.category', 1),
                ('metadata.identifier', 1),
                ('metadata.filename', 1)
            ], background=True)
            self.db['fs.files'].create_index([('filename', 1), ('uploadDate', -1)], background=True)
            self.db['fs.chunks'].create_index([('files_id', 1), ('n', 1)], unique=True, background=True)
        except Exception:
            pass

    def _full_filename(self, category, identifier, filename):
        return f"{category}/{identifier}/{filename}"

    def _query(self, category, identifier, filename):
        full = self._full_filename(category, identifier, filename)
        return {
            '$or': [
                {
                    'metadata.category': str(category),
                    'metadata.identifier': str(identifier),
                    'metadata.filename': str(filename)
                },
                {'filename': full}
            ]
        }

    def save(self, category, identifier, filename, content, content_type=None, extra_metadata=None):
        """Save an artifact to MongoDB GridFS and local cache.
        Replaces any existing artifact with the same category, identifier, and filename.
        """
        identifier = str(identifier)
        filename = Path(filename).name
        full_name = self._full_filename(category, identifier, filename)
        ctype = content_type or guess_type(filename)
        
        meta = {
            'category': category,
            'identifier': identifier,
            'filename': filename,
            'content_type': ctype,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            **(extra_metadata or {})
        }

        # Convert content to bytes
        if isinstance(content, (str, Path)):
            content_bytes = Path(content).read_bytes()
        elif hasattr(content, 'read'):
            if hasattr(content, 'seek'):
                content.seek(0)
            content_bytes = content.read()
            if isinstance(content_bytes, str):
                content_bytes = content_bytes.encode('utf-8')
        elif isinstance(content, bytes):
            content_bytes = content
        else:
            raise TypeError(f"Unsupported content type: {type(content)}")

        # Clean up any existing file with this name/metadata to prevent duplicates
        self.delete(category, identifier, filename)

        file_id = ObjectId()
        if self.bucket is not None:
            # Use PyMongo GridFSBucket streaming
            stream = io.BytesIO(content_bytes)
            uploaded_id = self.bucket.upload_from_stream(
                full_name,
                stream,
                chunk_size_bytes=CHUNK_SIZE,
                metadata=meta
            )
            file_id = uploaded_id
        else:
            # GridFS standard schema (compatible with mongomock or fallback)
            now = datetime.now(timezone.utc)
            total_len = len(content_bytes)
            chunks = [content_bytes[i:i + CHUNK_SIZE] for i in range(0, total_len, CHUNK_SIZE)] or [b'']
            for idx, chk in enumerate(chunks):
                self.db['fs.chunks'].insert_one({
                    '_id': ObjectId(),
                    'files_id': file_id,
                    'n': idx,
                    'data': chk
                })
            self.db['fs.files'].insert_one({
                '_id': file_id,
                'length': total_len,
                'chunkSize': CHUNK_SIZE,
                'uploadDate': now,
                'filename': full_name,
                'metadata': meta
            })

        # Cache locally in root directory if root is configured
        if self.root:
            local_path = self.root / category / identifier / filename
            local_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = local_path.with_name(f"{local_path.name}.{os.getpid()}.{file_id}.tmp")
            try:
                tmp_path.write_bytes(content_bytes)
                os.replace(tmp_path, local_path)
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

        return file_id

    def get_stream(self, category, identifier, filename):
        """Retrieve a download stream for an artifact from GridFS."""
        q = self._query(category, identifier, filename)
        doc = self.db['fs.files'].find_one(q, sort=[('uploadDate', -1)])
        if not doc:
            return None, None

        if self.bucket is not None:
            stream = self.bucket.open_download_stream(doc['_id'])
            return stream, doc
        else:
            chunks = list(self.db['fs.chunks'].find({'files_id': doc['_id']}).sort('n', 1))
            data = b''.join(c['data'] for c in chunks)
            return io.BytesIO(data), doc

    def get_bytes(self, category, identifier, filename):
        """Retrieve all bytes of an artifact.
        Checks local cache first, then GridFS.
        Raises FileNotFoundError if missing everywhere.
        """
        identifier = str(identifier)
        filename = Path(filename).name

        # 1. Check local cache
        if self.root:
            local = self.root / category / identifier / filename
            if local.exists() and local.is_file() and local.stat().st_size >= 0:
                return local.read_bytes()

        # 2. Check GridFS
        stream, doc = self.get_stream(category, identifier, filename)
        if stream is not None:
            data = stream.read()
            # Populate local cache
            if self.root:
                local = self.root / category / identifier / filename
                local.parent.mkdir(parents=True, exist_ok=True)
                tmp = local.with_name(f"{local.name}.{os.getpid()}.tmp")
                try:
                    tmp.write_bytes(data)
                    os.replace(tmp, local)
                finally:
                    if tmp.exists():
                        try:
                            tmp.unlink()
                        except OSError:
                            pass
            return data

        raise FileNotFoundError(f"Artifact not found: {category}/{identifier}/{filename}")

    def ensure_local(self, category, identifier, filename):
        """Ensure the artifact exists on the local filesystem.
        If missing locally, downloads it from GridFS.
        Returns Path to the local file.
        Raises FileNotFoundError if missing in GridFS.
        """
        identifier = str(identifier)
        filename = Path(filename).name

        if not self.root:
            raise ValueError("Root directory not configured for local cache")

        target = self.root / category / identifier / filename
        if target.exists() and target.is_file() and target.stat().st_size > 0:
            return target

        # Fetch from GridFS
        stream, doc = self.get_stream(category, identifier, filename)
        if stream is None:
            raise FileNotFoundError(f"Artifact not found: {category}/{identifier}/{filename}")

        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.{os.getpid()}.{doc['_id']}.tmp")
        try:
            with tmp.open('wb') as f:
                while True:
                    chunk = stream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

        return target

    def exists(self, category, identifier, filename):
        """Check if an artifact exists in GridFS or local cache."""
        if self.root:
            local = self.root / category / str(identifier) / Path(filename).name
            if local.exists() and local.is_file() and local.stat().st_size > 0:
                return True
        q = self._query(category, identifier, filename)
        return self.db['fs.files'].count_documents(q) > 0

    def delete(self, category, identifier, filename=None):
        """Delete an artifact or all artifacts for an identifier safely."""
        identifier = str(identifier)
        if filename is not None:
            filename = Path(filename).name
            q = self._query(category, identifier, filename)
            for doc in self.db['fs.files'].find(q):
                file_id = doc['_id']
                if self.bucket is not None:
                    try:
                        self.bucket.delete(file_id)
                    except Exception:
                        self.db['fs.files'].delete_one({'_id': file_id})
                        self.db['fs.chunks'].delete_many({'files_id': file_id})
                else:
                    self.db['fs.files'].delete_one({'_id': file_id})
                    self.db['fs.chunks'].delete_many({'files_id': file_id})
            if self.root:
                local = self.root / category / identifier / filename
                if local.exists():
                    try:
                        local.unlink()
                    except OSError:
                        pass
        else:
            # Delete all artifacts for this category and identifier
            q = {
                '$or': [
                    {'metadata.category': category, 'metadata.identifier': identifier},
                    {'filename': {'$regex': f"^{category}/{identifier}/"}}
                ]
            }
            for doc in self.db['fs.files'].find(q):
                file_id = doc['_id']
                if self.bucket is not None:
                    try:
                        self.bucket.delete(file_id)
                    except Exception:
                        self.db['fs.files'].delete_one({'_id': file_id})
                        self.db['fs.chunks'].delete_many({'files_id': file_id})
                else:
                    self.db['fs.files'].delete_one({'_id': file_id})
                    self.db['fs.chunks'].delete_many({'files_id': file_id})
            if self.root:
                dir_path = self.root / category / identifier
                if dir_path.exists() and dir_path.is_dir():
                    import shutil
                    try:
                        shutil.rmtree(dir_path)
                    except OSError:
                        pass

    def list_artifacts(self, category=None, identifier=None):
        """List stored artifacts with metadata."""
        filter_doc = {}
        if category:
            filter_doc['metadata.category'] = category
        if identifier:
            filter_doc['metadata.identifier'] = str(identifier)
        results = []
        for doc in self.db['fs.files'].find(filter_doc, sort=[('uploadDate', -1)]):
            results.append({
                'id': str(doc['_id']),
                'filename': doc.get('filename'),
                'length': doc.get('length', 0),
                'uploadDate': doc.get('uploadDate'),
                'metadata': doc.get('metadata', {})
            })
        return results
