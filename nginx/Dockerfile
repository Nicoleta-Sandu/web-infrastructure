FROM nginx:1.23-alpine

# Copy Nginx configuration files
COPY conf/nginx.conf /etc/nginx/nginx.conf
COPY conf/app.conf /etc/nginx/conf.d/default.conf

# Copy static content
COPY html /usr/share/nginx/html

# Remove the user directive from nginx.conf since we'll run as non-root
RUN sed -i '1d' /etc/nginx/nginx.conf

# Update the pid path to a location in tmpfs that will be mounted by docker-compose
RUN sed -i 's|pid /var/run/nginx.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf

# Modify app.conf to use /tmp for logs instead of /var/log/nginx
RUN sed -i 's|/var/log/nginx/app_access.log|/tmp/app_access.log|g' /etc/nginx/conf.d/default.conf && \
    sed -i 's|/var/log/nginx/app_error.log|/tmp/app_error.log|g' /etc/nginx/conf.d/default.conf

# Also update the main nginx.conf to use /tmp for access logs
RUN sed -i 's|/var/log/nginx/access.log|/tmp/access.log|g' /etc/nginx/nginx.conf && \
    sed -i 's|/var/log/nginx/error.log|/tmp/error.log|g' /etc/nginx/nginx.conf

# Create a non-root user to run Nginx
RUN adduser -D -H -u 1000 -s /sbin/nologin nginxuser && \
    chown -R nginxuser:nginxuser /usr/share/nginx/html && \
    # Ensure entrypoint scripts are executable
    chmod +x /docker-entrypoint.sh && \
    chmod -R +x /docker-entrypoint.d/

# Switch to non-root user
USER nginxuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1