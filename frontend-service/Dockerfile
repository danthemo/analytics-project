FROM node:20-alpine

WORKDIR /app

COPY frontend-service/package.json frontend-service/package-lock.json ./
RUN npm ci

COPY frontend-service /app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
