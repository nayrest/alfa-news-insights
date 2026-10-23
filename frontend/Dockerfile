FROM node:20.18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_USE_MOCKS=false
ARG VITE_API_URL=/api
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine
# BACKEND_URL подставляется в шаблон nginx при старте контейнера
ENV BACKEND_URL=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
