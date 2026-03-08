FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Build for production
RUN npm run build

# Serve via Vite preview to avoid aggressive cache during testing
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
