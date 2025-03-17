# Use the provided base image
FROM ghcr.io/berriai/litellm:main-latest

RUN pip install pangea-sdk==5.5.0b4

WORKDIR /app

# Copy the configuration file into the container at /app
COPY ./pangea_litellm.py .

# Make sure your docker/entrypoint.sh is executable
RUN chmod +x ./docker/entrypoint.sh

# Expose the necessary port
EXPOSE 4000/tcp

# Override the CMD instruction with your desired command and arguments
# WARNING: FOR PROD DO NOT USE `--detailed_debug` it slows down response times, instead use the following CMD
# CMD ["--port", "4000", "--config", "config.yaml"]

CMD ["--port", "4000", "--config", "config.yaml", "--detailed_debug"]
