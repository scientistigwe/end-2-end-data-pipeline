# backend/api/flask_app/pipeline/recommendations/recommendation_service.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
   MessageType,
   ProcessingMessage,
   ComponentType,
   ModuleIdentifier,
   MessageMetadata
)
from core.staging.staging_manager import StagingManager

logger = logging.getLogger(__name__)

def initialize_services(app):
   services = {
       'recommendation_service': RecommendationService(
           staging_manager=staging_manager,
           message_broker=message_broker,
           initialize_async=True
       )
   }
   return services

class RecommendationService:
   def __init__(self, staging_manager, message_broker, initialize_async=False):
       self.staging_manager = staging_manager
       self.message_broker = message_broker
       self.logger = logger

       self.module_identifier = ModuleIdentifier(
           component_name="recommendation_service",
           component_type=ComponentType.RECOMMENDATION_SERVICE,
           department="recommendation",
           role="service"
       )

       if initialize_async:
           asyncio.run(self._initialize_async())

   async def _initialize_async(self):
       await self._initialize_message_handlers()

   async def _initialize_message_handlers(self) -> None:
       handlers = {
           MessageType.RECOMMENDATION_START: self._handle_recommendation_request,
           MessageType.RECOMMENDATION_STATUS_REQUEST: self._handle_status_request,
           MessageType.RECOMMENDATION_REPORT_REQUEST: self._handle_report_request,
           MessageType.RECOMMENDATION_ACTION_REQUEST: self._handle_action_request,
           MessageType.RECOMMENDATION_DISMISS_REQUEST: self._handle_dismiss_request,
           MessageType.RECOMMENDATION_ERROR: self._handle_error
       }

       for message_type, handler in handlers.items():
           await self.message_broker.subscribe(
               module_identifier=self.module_identifier,
               message_patterns=f"recommendation.{message_type.value}.#",
               callback=handler
           )

   async def _handle_recommendation_request(self, message: ProcessingMessage) -> None:
       try:
           control_point_id = message.content.get('control_point_id')
           request_data = message.content.get('request_data', {})

           staged_id = await self.staging_manager.store_incoming_data(
               request_data.get('pipeline_id'),
               request_data,
               source_type='recommendation_generation',
               metadata={
                   'control_point_id': control_point_id,
                   'type': 'recommendation_request'
               },
           )

           await self.message_broker.publish(
               ProcessingMessage(
                   message_type=MessageType.RECOMMENDATION_START,
                   content={
                       'pipeline_id': request_data.get('pipeline_id'),
                       'staged_id': staged_id,
                       'config': request_data.get('config', {}),
                       'control_point_id': control_point_id
                   },
                   metadata=MessageMetadata(
                       source_component=self.module_identifier.component_name,
                       target_component="recommendation_manager",
                       correlation_id=message.metadata.correlation_id
                   )
               )
           )

       except Exception as e:
           self.logger.error(f"Failed to handle recommendation request: {str(e)}")
           await self._notify_error(message, str(e))

   async def _handle_status_request(self, message: ProcessingMessage) -> None:
       try:
           staged_id = message.content.get('staged_id')
           staged_data = await self.staging_manager.retrieve_data(
               staged_id,
               'RECOMMENDATION'
           )
           if not staged_data:
               raise ValueError(f"Recommendation {staged_id} not found")

           await self.message_broker.publish(
               ProcessingMessage(
                   message_type=MessageType.RECOMMENDATION_STATUS_RESPONSE,
                   content={
                       'staged_id': staged_id,
                       'status': staged_data.get('status', 'unknown'),
                       'progress': staged_data.get('progress', 0),
                       'created_at': staged_data.get('created_at'),
                       'error': staged_data.get('error')
                   },
                   metadata=MessageMetadata(
                       source_component=self.module_identifier.component_name,
                       target_component=message.metadata.source_component,
                       correlation_id=message.metadata.correlation_id
                   )
               )
           )

       except Exception as e:
           self.logger.error(f"Failed to handle status request: {str(e)}")
           await self._notify_error(message, str(e))

   async def _handle_report_request(self, message: ProcessingMessage) -> None:
       try:
           staged_id = message.content.get('staged_id')
           staged_data = await self.staging_manager.retrieve_data(
               staged_id,
               'RECOMMENDATION'
           )
           if not staged_data:
               raise ValueError(f"Recommendation {staged_id} not found")

           await self.message_broker.publish(
               ProcessingMessage(
                   message_type=MessageType.RECOMMENDATION_REPORT_RESPONSE,
                   content={
                       'staged_id': staged_id,
                       'pipeline_id': staged_data.get('pipeline_id'),
                       'type': staged_data.get('recommendation_type'),
                       'results': staged_data.get('results', {}),
                       'metadata': staged_data.get('metadata', {}),
                       'created_at': staged_data.get('created_at')
                   },
                   metadata=MessageMetadata(
                       source_component=self.module_identifier.component_name,
                       target_component=message.metadata.source_component,
                       correlation_id=message.metadata.correlation_id
                   )
               )
           )

       except Exception as e:
           self.logger.error(f"Failed to handle report request: {str(e)}")
           await self._notify_error(message, str(e))

   async def _handle_error(self, message: ProcessingMessage) -> None:
       error = message.content.get('error', 'Unknown error')
       self.logger.error(f"Recommendation error received: {error}")
       await self._notify_error(message, error)

   async def _notify_error(self, original_message: ProcessingMessage, error: str) -> None:
       await self.message_broker.publish(
           ProcessingMessage(
               message_type=MessageType.SERVICE_ERROR,
               content={
                   'service': self.module_identifier.component_name,
                   'error': error,
                   'original_message': original_message.content
               },
               metadata=MessageMetadata(
                   source_component=self.module_identifier.component_name,
                   target_component="control_point_manager",
                   correlation_id=original_message.metadata.correlation_id
               )
           )
       )

   async def cleanup(self) -> None:
       try:
           await self.message_broker.unsubscribe_all(
               self.module_identifier.component_name
           )
       except Exception as e:
           self.logger.error(f"Cleanup failed: {str(e)}")

   async def _handle_dismiss_request(self, message: ProcessingMessage) -> None:
       """Handle recommendation dismiss request"""
       try:
           staged_id = message.content.get('staged_id')
           recommendation_id = message.content.get('recommendation_id')
           dismiss_data = message.content.get('dismiss_data', {})

           # Get staged data to validate recommendation exists
           staged_data = await self.staging_manager.retrieve_data(
               staged_id,
               'RECOMMENDATION'
           )
           if not staged_data:
               raise ValueError(f"Recommendation {staged_id} not found")

           # Forward dismiss to recommendation manager
           await self.message_broker.publish(
               ProcessingMessage(
                   message_type=MessageType.RECOMMENDATION_DISMISS,
                   content={
                       'staged_id': staged_id,
                       'recommendation_id': recommendation_id,
                       'reason': dismiss_data.get('reason'),
                       'timestamp': datetime.utcnow().isoformat()
                   },
                   metadata=MessageMetadata(
                       source_component=self.module_identifier.component_name,
                       target_component="recommendation_manager",
                       correlation_id=message.metadata.correlation_id
                   )
               )
           )

       except Exception as e:
           self.logger.error(f"Failed to handle dismiss request: {str(e)}")
           await self._notify_error(message, str(e))

   async def _handle_action_request(self, message: ProcessingMessage) -> None:
           """Handle recommendation action request"""
           try:
               staged_id = message.content.get('staged_id')
               recommendation_id = message.content.get('recommendation_id')
               action_data = message.content.get('action_data', {})

               # Get staged data to validate recommendation exists
               staged_data = await self.staging_manager.retrieve_data(
                   staged_id,
                   'RECOMMENDATION'
               )
               if not staged_data:
                   raise ValueError(f"Recommendation {staged_id} not found")

               # Forward action to recommendation manager
               await self.message_broker.publish(
                   ProcessingMessage(
                       message_type=MessageType.RECOMMENDATION_ACTION,
                       content={
                           'staged_id': staged_id,
                           'recommendation_id': recommendation_id,
                           'action': action_data,
                           'timestamp': datetime.utcnow().isoformat()
                       },
                       metadata=MessageMetadata(
                           source_component=self.module_identifier.component_name,
                           target_component="recommendation_manager",
                           correlation_id=message.metadata.correlation_id
                       )
                   )
               )

           except Exception as e:
               self.logger.error(f"Failed to handle action request: {str(e)}")
               await self._notify_error(message, str(e))

