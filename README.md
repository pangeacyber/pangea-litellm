
<a href="https://pangea.cloud?utm_source=github&utm_medium=gw-network" target="_blank" rel="noopener noreferrer">
  <img src="https://pangea-marketing.s3.us-west-2.amazonaws.com/pangea-color.svg" alt="Pangea Logo" height="40" />
</a>

[![documentation](https://img.shields.io/badge/documentation-pangea-blue?style=for-the-badge&labelColor=551B76)](https://pangea.cloud/docs/)
[![Contact](https://img.shields.io/badge/Discourse-4A154B?style=for-the-badge&logo=discourse&logoColor=white)][Contact]

[Contact]: mailto:info@pangea.cloud


# Pangea LiteLLM Plugin

The Pangea LiteLLM Plugin is a powerful tool that enhances the functionality of the LiteLLM Gateway. It provides additional features and capabilities to help you manage and secure your APIs effectively. Pangea LiteLLM Plugin main feature is to pre-process AI requests using our [Pangea AI Guard](https://pangea.cloud/services/ai-guard/) service.  Using this plugin together with AI Guard enables LLM prompts and responses to gain access to numerous security guardrails such as blocking prompt injection attacks or preventing PII/sensitive data leakage.


## Getting Started

To get started with the Pangea LiteLLM Plugin, follow these steps:

### Prerequisites

1. Make sure you have the following prerequisites installed on your machine:

- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Curl

2. Get a [Pangea token for the AI Guard service and its domain](https://pangea.cloud/docs/ai-guard/#get-a-free-pangea-account-and-enable-the-ai-guard-service).


### Build

In order to build Pangea LiteLLM Plugin image run:

```bash
docker build --no-cache . --tag litellm_plugin
```

### Setup

In order to run `litellm_plugin` image we need to understand some settings in the `compose.yaml` file.

```yaml
services:
  pangea-litellm-plugin:
    container_name: pangea-litellm-container
    image: litellm_plugin
    volumes:
  	- ./config/config.yaml:/app/config.yaml
  	- ./config/pangea_config.json:/app/pangea_config.json
    ports:
  	- "4000:4000"
  	- "8011:8001"
  	- "8012:8002"
    environment:
  	PANGEA_LL_CONFIG_FILE: /app/pangea_config.json
  	PANGEA_AI_GUARD_TOKEN: ${PANGEA_AI_GUARD_TOKEN}
    command: ["--port", "4000", "--config", "/app/config.yaml", "--detailed_debug"]
```

The sections of the file are described below:

#### Environment Variables

Environment variables are set in the following section of the `compose.yaml` file:

```yaml
services:
  pangea-litellm-plugin:
    environment:
```

1. Pangea AI Guard Token: This token is needed to make requests to Pangea AI Guard service. In order to load it on the plugin it should be saved into the `PANGEA_AI_GUARD_TOKEN`environment variable. It should be done on the `compose.yaml` file, not in the `Dockerfile`. NOTE: To inject environment variables with sensitive information in a Dockerfile [Docker Secrets](https://docs.docker.com/compose/how-tos/use-secrets/) should be used.

To set this environment variable run the following command using the Pangea token you previously generated as its value:

```bash
export PANGEA_AI_GUARD_TOKEN=”pts_…”
```

2. `PANGEA_LL_CONFIG_FILE` is set to the Pangea LiteLLM Config file location. This file should be mounted in the `volumes` section of the `compose.yaml` file. In this example it is set to `/app/pangea_config.json` due to in `volumes` sections we have:
```yaml
    volumes:
      - ./config/pangea_config.json:/app/pangea_config.json
```
	This means that `./config/pangea_config.json` in our local machine is mounted into `/app/pangea_config.json` on the Pangea Plugin docker. The Pangea LiteLLM Plugin configuration file will be documented in a later section.


#### Volumes

To allow docker to access a local file it must be declared in the `volumes` section in the `compose.yaml` file.
```yaml
    volumes:
      - <origin>:<destination>
```
It is possible to map this origin from whatever location in our local machine to whatever destination into the docker but it is important to take care about location permissions. Also the `destination` path should be saved into the environment variable `PANGEA_LL_CONFIG_FILE` so it can be loaded by the plugin.  In this example the relative path `./config` makes reference to the root directory where the `compose.yaml` file is located.


### LiteLLM Config File

In the file `./config/config.yaml`:
1. Set the api_key to your OpenAI api key 
2. Set the organization to your OpenAI organization ID

```yaml
model_list:
  - model_name: openai-gpt-3.5
litellm_params:
  model: openai/gpt-3.5-turbo
  api_key: sk-proj-...
  organization: org-...
  temperature: 0.2

litellm_settings:
  callbacks: pangea_litellm.proxy_handler_instance # sets litellm.callbacks = [proxy_handler_instance]
```

To learn more about LiteLLM Config [click here.](https://docs.litellm.ai/docs/proxy/configs)


### Pangea Plugin Config File

In the file `./config/pangea_config.json`:
1. Set the pangea_domain field to the domain of your AI Guard configuration.
2. Set the recipe field to a recipe that exists in your AI guard configuration.

```jsonc
{
  "pangea_domain": "aws.us.pangea.cloud",   // Pangea Domain got from Pangea Console
  "insecure": true,                     	// Set to true to use http connections
  "log_level": "debug",                 	// Log level used for logging
  "rules": [
	{
  	"model": "openai/gpt-3.5-turbo",  	// Model on the original request. It is used to translate request into AI Guard format
  	"allow_on_error": false,          	// Whether or not request will reach the LLM in case AI Guard request fails
  	"ai_guard": {
    	"request": {                    	// Pangea AI Guard default parameters
      	"parameters": {
        	"recipe": "pangea_prompt_guard"  	// Pangea AI Guard recipe
      	}
    	}
  	}
	}
  ]
}
```

### Run

After building and following all the configuration steps, it is ready to run. To start the environment run:
```bash
docker-compose up -d
```

### Test

To check it is running properly, run this next request:

```bash
curl -H "Accept: application/json" http://localhost:4000
```

and should return something like:

```html
<!DOCTYPE html>
	<html>
	<head>
	<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
	<link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
	<title>LiteLLM API - Swagger UI</title>
	</head>
	<body>
	<div id="swagger-ui">
	</div>
	<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
	<!-- `SwaggerUIBundle` is now available on the page -->
	<script>
	const ui = SwaggerUIBundle({
    	url: '/openapi.json',
    	"dom_id": "#swagger-ui",
    	"layout": "BaseLayout",
    	"deepLinking": true,
    	"showExtensions": true,
    	"showCommonExtensions": true,
    	oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
    	presets: [
        	SwaggerUIBundle.presets.apis,
        	SwaggerUIBundle.SwaggerUIStandalonePreset
    	],
	})
	</script>
	</body>
	</html>
```


## Usage

In these examples an Open AI Key is needed. Save it in an environment variable called `OPENAI_API_KEY`.

```bash
export OPENAI_API_KEY=”sk-proj-...”
```

### Valid request

Request:
```bash
curl "http://localhost:4000/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
  "model": "openai/gpt-3.5-turbo",
  "messages": [
	{"role": "system", "content": "you are a helpful assistant"},
	{"role": "user", "content": "Please echo back the following string <10.10.10.123>"}
  ]
}'
```

Response:
```json
{
	"id": "chatcmpl-BC8GqtS2PPdd15lqR4emNc4ZT0vvc",
	"created": 1742231428,
	"model": "gpt-3.5-turbo-0125",
	"object": "chat.completion",
	"system_fingerprint": null,
	"choices": [
    	{
        	"finish_reason": "stop",
        	"index": 0,
        	"message": {
            	"content": "<****>",
            	"role": "assistant",
            	"tool_calls": null,
            	"function_call": null
        	}
    	}
	],
	"usage": {
    	"completion_tokens": 4,
    	"prompt_tokens": 25,
    	"total_tokens": 29,
    	"completion_tokens_details": {
        	"accepted_prediction_tokens": 0,
        	"audio_tokens": 0,
        	"reasoning_tokens": 0,
        	"rejected_prediction_tokens": 0
    	},
    	"prompt_tokens_details": {
        	"audio_tokens": 0,
        	"cached_tokens": 0
    	}
	},
	"service_tier": "default"
}
```


### Rejected request

In this next example request send a malicious IP ("190.28.74.251") into the payload, so it will be rejected by AI Guard. Also, as Pangea Plugin Config have set `allow_on_error` to `false`, it return an error.

```bash
curl "http://localhost:4000/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
  "model": "openai/gpt-3.5-turbo",
  "messages": [
	{"role": "system", "content": "you are a helpful assistant"},
	{"role": "user", "content": "Please echo back the following string <190.28.74.251>"}
  ]
}'
```

Response:
```json
{
	"error": {
    	"message": "{'error': 'Prompt Injection was detected and blocked.  Confidential and PII was detected and redacted.'}",
    	"type": "None",
    	"param": "None",
    	"code": "400"
	}
}
```


## Contributing

We welcome contributions from the community to improve and expand the capabilities of the Pangea LiteLLM Plugin. If you would like to contribute, please follow the guidelines outlined in the CONTRIBUTING.md file.

## License

The Pangea LiteLLM Plugin is released under the [MIT License](https://opensource.org/licenses/MIT). Feel free to use, modify, and distribute it according to the terms of the license.

