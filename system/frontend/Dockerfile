# Stage 1: Build the Flutter Web App
FROM debian:bookworm-slim AS build-env

# Install dependencies required by Flutter
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Workaround for Podman/rootless Docker UID ownership issues during tar extraction.
# Using printf guarantees newlines are correctly interpreted.
RUN printf '#!/bin/sh\nexec /usr/bin/tar --no-same-owner "$@"\n' > /usr/local/bin/tar && \
    chmod +x /usr/local/bin/tar

# Clone the stable branch of the Flutter SDK
RUN git clone -b stable https://github.com/flutter/flutter.git /usr/local/flutter
ENV PATH="/usr/local/flutter/bin:/usr/local/flutter/bin/cache/dart-sdk/bin:${PATH}"

# Enable Web support
RUN flutter config --enable-web

WORKDIR /app

# Copy the dependencies specification file and fetch packages
COPY pubspec.yaml .
RUN flutter pub get

# Copy the frontend code, remove unnecessary non-web platforms to bypass Gradle downloads, and build
COPY . .
RUN rm -rf android ios windows linux macos test && \
    flutter build web --release

# Stage 2: Serve the compiled files with Nginx
FROM nginx:alpine
COPY --from=build-env /app/build/web /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
