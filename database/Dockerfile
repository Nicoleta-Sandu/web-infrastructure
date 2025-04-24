FROM postgres:15-alpine

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Copy custom PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Run as postgres user
USER postgres

# Set environment variables
ENV POSTGRES_PASSWORD=postgres_password
ENV POSTGRES_USER=postgres
ENV POSTGRES_DB=postgres

# Use custom configuration
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD pg_isready -U postgres || exit 1