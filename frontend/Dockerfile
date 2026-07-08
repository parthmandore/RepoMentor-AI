FROM node:20-alpine

WORKDIR /app

# Install package configurations
COPY package.json package-lock.json* ./
RUN npm install

# Copy application files and build
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

EXPOSE 3000

# Start production server
CMD ["npm", "run", "start"]
