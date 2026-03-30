FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --only=production || npm install --omit=dev
COPY . .
RUN npm run build || true
CMD ["node", "dist/agent.js"]
