import json
import os
import pathlib
from traceback import format_exception
import typing as t

from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
from typing import Optional, Literal
from fastapi import HTTPException


from pangea import PangeaConfig
from pangea.services.ai_guard import AIGuard

token = os.getenv("PANGEA_AI_GUARD_TOKEN", "")

DEFAULT_PANGEA_DOMAIN = "aws.us.pangea.cloud"


class Log():
    LEVELS = {
        "none": 0,
        "error": 1,
        "warn": 2,
        "info": 3,
        "debug": 4
    }

    def __init__(self):
        self.level = self.LEVELS[os.getenv("PANGEA_LOG_LEVEL", "warn").lower()]
        self.warning = self.warn

    def error(self, msg):
        if self.level >= Log.LEVELS["error"]:
            print(f"PANGEA: ERROR: {msg}")

    def warn(self, msg):
        if self.level >= Log.LEVELS["warn"]:
            print(f"PANGEA: WARN: {msg}")

    def info(self, msg):
        if self.level >= Log.LEVELS["info"]:
            print(f"PANGEA: INFO: {msg}")

    def debug(self, msg):
        if self.level >= Log.LEVELS["debug"]:
            print(f"PANGEA: DEBUG: {msg}")


log = Log()


class Operation:
    def __init__(self, op_params: dict):
        self.json = op_params.copy()
        if "recipe" not in self.json:
            self.json["recipe"] = "pangea_prompt_guard"


class Rule:
    def __init__(self, rule: dict):
        self.rule = rule.copy()
        self.model = self.rule.get("model")
        self.allow_failure = self.rule.get("allow_on_error", False)

    def match(self, model) -> bool:
        if model != self.model:
            log.debug(f"failed to match {model} to {self.model}")
            return False
        return True

    def operation_params(self, op, service="ai_guard") -> t.Optional[Operation]:
        svc = self.rule.get(service)
        if not svc:
            return None
        info = svc.get(op, {}).get("parameters")
        if info is None or not info.get("enabled", True):
            return None
        return Operation(info)


default_config = {
  "pangea_domain": DEFAULT_PANGEA_DOMAIN,
  "rules": [
    {
      "host": "localhost",
      "endpoint": "/chat/completions",
      "allow_on_error": False,
      "protocols": ["http"],
      "ports": ["4000"],
      "audit_values": {
        "model": "openai/gpt-3.5-turbo"
      },
      "ai_guard": {
        "request": {
          "parameters": {
            "recipe": "pangea_prompt_guard",
          }
        },
        "response": {
        }
      }
    }
  ]
}


class PangeaLLConfig:
    def __init__(self, j: dict):
        self.domain = j.get("pangea_domain")
        self.insecure = j.get("insecure", False)
        self.header_recipe_map = j.get("headers", {})
        log_level = j.get("log_level")
        if log_level:
            log.level = Log.LEVELS.get(log_level, log.level)
        if not self.domain:
            self.domain = DEFAULT_PANGEA_DOMAIN
        rules = j.get("rules", [])
        self.rules: t.List[Rule] = []
        for i, rule in enumerate(rules):
            if not rule.get("model"):
                log.warning(f"Rule {i} is missing the model which is required. Ignoring rule")
                continue
            self.rules.append(Rule(rule))

    def match_rule(self, data: dict) -> t.Optional[Rule]:
        model = data["model"]
        log.debug(f"rules: {self.rules}")
        for rule in self.rules:
            if rule.match(model):
                return rule

        return None

def load_config():
    loc = os.getenv("PANGEA_LL_CONFIG_FILE")
    if not loc:
        pth = pathlib.Path(__file__).parent / "pangea_config.json"
    else:
        pth = pathlib.Path(loc)
    if pth.exists():
        json_config = json.load(open(pth))
        return PangeaLLConfig(json_config)
    else:
        log.warning(f"No config provided, using default")
        return PangeaLLConfig(default_config)


config = load_config()


class PangeaHandler(CustomLogger):
    def __init__(self):
        kwargs = {
            "domain": "dev.aws.pangea.cloud",  # config.domain,
        }
        if not config.domain.endswith(".pangea.cloud"):
            kwargs["environment"] = "local"
        if config.insecure:
            kwargs["insecure"] = True

        self.ai_guard = AIGuard(token, config=PangeaConfig(**kwargs))

    async def async_pre_call_hook(self, user_api_key_dict: UserAPIKeyAuth, cache: DualCache, data: dict, call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            # 'pass_through_endpoint',
            # 'rerank'
        ]):

        log.debug(f"PANGEA DICT: {data.keys()}")
        log.debug(f"PANGEA META: {data['metadata']}")
        log.debug(f"PANGEA MODEL: {data['model']}")
        allow_failure = False
        try:
            if call_type not in ("completion", "text_completion"):
                return
            rule = config.match_rule(data)
            if not rule:
                log.debug(f"No rule matched {data.get('model')}, allowing")
                return
            allow_failure = rule.allow_failure is True
            op = rule.operation_params("request")
            if op is None:
                log.debug(f"No work for 'request', allowing")
                return

            # recipe is in the config, but can be overridden by this header
            recipe = data["metadata"].get("headers", {}).get('x-pangea-aig-recipe')
            log.debug(f"PANGEA recipe from custom header {recipe}")
            # can be further overridden by the configured header/recipe map
            for header_name, recipe_map in config.header_recipe_map.items():
                header_name = header_name.lower()
                header_value = data["metadata"].get("headers", {}).get(header_name)
                if not header_value:
                    continue
                if header_value in recipe_map:
                    recipe = recipe_map[header_value]
            if recipe:
                log.debug(f"PANGEA final recipe: {recipe}")
                op.json["recipe"] = recipe
            # not sure about this parsing or how its going to differ between providers, so opting to use
            # everything after the / as the model and not providing a version to the log
            # maybe import the translator and let it parse the model?
            provider, model = data['model'].split('/', 1)
            log_fields = {
                "model": f'{{"provider": "{provider}", "model": "{model}"}}',
                # this is the incoming API not the outgoing one
                "extra_info": f'{{"api": "{data["metadata"]["endpoint"]}"}}',
            }
            op.json["log_fields"] = log_fields
            log.debug(f"PANGEA OP: {json.dumps(op.json)}")
            response = self.ai_guard.guard_text(messages=data["messages"], **op.json)
            log.debug(f"PANGEA RESPONSE: {json.dumps(response.json)}")
            if response.http_status != 200:
                log.error(f"Failed to call AI Guard: {response.status_code}, {response.text}")
                raise Exception("Failed to call AI Guard")
            blocked = response.json["result"].get("blocked", False)
            if blocked:
                raise HTTPException(
                    status_code=400, detail={"error": response.json['summary']}
                )
            new_messages = response.json["result"].get("prompt_messages")
            if new_messages:
                data["messages"] = new_messages
        except HTTPException as e:
            raise  # need to let this float up
        except Exception as e:
            log.error(f"Exception while trying to call AI Guard:\n {format_exception(e)}")
            if not allow_failure:
                raise HTTPException(
                    status_code=400, detail={"error": "Prompt has been rejected"}
                )
        return data


proxy_handler_instance = PangeaHandler()
