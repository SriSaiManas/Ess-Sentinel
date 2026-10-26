FROM node:24-bookworm-slim AS node
FROM python:3.12-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY package.json package-lock.json ./
COPY client/package.json client/package.json
COPY server/package.json server/package.json
RUN npm ci
COPY ml-service/requirements-tested.txt ml-service/requirements-tested.txt
RUN pip install --no-cache-dir -r ml-service/requirements-tested.txt
COPY . .
RUN python scripts/rebuild_demo.py && npm run build
ENV NODE_ENV=production PORT=3001 ARTIFACT_DIR=/data/artifacts PYTHON_BIN=python
RUN useradd -m ess && mkdir -p /data/artifacts && chown -R ess:ess /app /data
USER ess
EXPOSE 3001
CMD ["npm","start"]
