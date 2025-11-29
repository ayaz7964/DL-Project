# Use node image to build React app
FROM node:18 as build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Use nginx to serve the build folder
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 for frontend
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
