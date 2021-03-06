# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import os
import json
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.interfaces.alexa.presentation.apl import (RenderDocumentDirective)

from ask_sdk_model import Response


import searchClient

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome to the Developer Office Hours Video library search."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class SearchIntentHandler(AbstractRequestHandler):
    """Handler for Search Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SearchIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        request = handler_input.request_envelope.request
        querySlot = request.intent.slots["query"]

        # speak_output = querySlot.value

        query_results = searchClient.perform_search(querySlot.value)


        source = []
        for result in query_results:
            source.append({ 
                "offset": result["results"][0]['offset'],
                "url": result["url"],
                "description": result['description'],
                "lengthInSeconds": result['lengthInSeconds'],
                "title": result['title']
            })

        # {
        #                                 "description": "${payload.queryResults.episodes[episodeIndex].description}",
        #                                 "offset": "${payload.queryResults.episodes[episodeIndex].results[resultIndex].offset}",
        #                                 "url": "${payload.queryResults.episodes[episodeIndex].url}"
        #                             }


        logging.info(query_results)

        with open("./docs/videoplayer.json") as apl_doc:
            apl_json = json.load(apl_doc)

            if ask_utils.get_supported_interfaces(handler_input).alexa_presentation_apl is not None:
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_json,
                        datasources={
                            "queryResults": {
                                "episodes": query_results,
                                "source": source
                            },
                            "videoplayerData": {
                                "transformers": [
                                {
                                    "inputPath": "spokenSsml",
                                    "outputName": "speech",
                                    "transformer": "ssmlToSpeech"
                                },
                                {
                                    "inputPath": "spokenSsml",
                                    "outputName": "spokenText",
                                    "transformer": "ssmlToText"
                                }
                                ],
                                "type": "object",
                                "properties": {
                                    "displayText": "Here are your search results",
                                    "spokenText": "Here are your search results",
                                    "spokenSsml": "<speak>Here are your search results</speak>"
                                }
                            }
                        }
                    )
                )


        # reprompt = "was that helpful?"


        return (
            handler_input.response_builder
                # .speak(speak_output)
                # .ask(reprompt)
                .response
        )


class HandleUserInputHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.request_util.get_request_type(handler_input) == 'Alexa.Presentation.APL.UserEvent'

    def handle(self, handler_input):
        # do nothing for right now
        return (handler_input.response_builder.response)





#### DEFAULT HANDLERS
class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logging.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logging.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SearchIntentHandler())
sb.add_request_handler(HandleUserInputHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

# lambda_handler = sb.lambda_handler()

def lambda_handler(event, context):
    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                        'DEBUG', 'INFO',
                        'WARNING', 'ERROR',
                        'CRITICAL'
                    ]:
      log_level = 'INFO'
    logging.getLogger().setLevel(log_level)

    logging.info(json.dumps(event))

    response = sb.lambda_handler()(event, context)

    logging.info(json.dumps(response))
    return response

