#!/usr/bin/env python3

import asyncio
import websockets
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Set
from monitoring import MonitoringClient


class DashboardServer:
    def __init__(self, host="localhost", port=8765, monitoring_url="http://localhost:9090"):
        self.host = host
        self.port = port
        self.monitoring_client = MonitoringClient(monitoring_url)
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.experiment_status = {
            "running": False,
            "name": None,
            "start_time": None,
            "duration": 0,
            "target_service": None
        }
        self.metrics_history = []
        self.baseline_metrics = {}
        self.streaming = False
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        logging.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send current experiment status and recent metrics
        await self.send_to_client(websocket, {
            "type": "experiment_status",
            "data": self.experiment_status
        })
        
        if self.metrics_history:
            await self.send_to_client(websocket, {
                "type": "metrics_history",
                "data": self.metrics_history[-50:]  # Last 50 data points
            })

    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        logging.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def send_to_client(self, websocket, message):
        """Send message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)

    async def broadcast(self, message):
        """Broadcast message to all connected clients"""
        if self.clients:
            disconnected = []
            for client in self.clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                await self.unregister_client(client)

    async def handle_client_message(self, websocket, message):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "start_metrics_stream":
                service = data.get("service", "web-server")
                await self.start_metrics_streaming(service)
            elif action == "stop_metrics_stream":
                await self.stop_metrics_streaming()
            elif action == "get_baseline":
                service = data.get("service", "web-server")
                await self.capture_baseline(service)
                
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON received from client: {message}")

    async def client_handler(self, websocket, path):
        """Handle WebSocket client connections"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

    async def start_metrics_streaming(self, target_service):
        """Start streaming metrics for a service"""
        if self.streaming:
            return
            
        self.streaming = True
        self.experiment_status["target_service"] = target_service
        
        await self.broadcast({
            "type": "stream_started",
            "data": {"service": target_service}
        })
        
        # Start background task for metrics collection
        asyncio.create_task(self.metrics_collection_loop(target_service))

    async def stop_metrics_streaming(self):
        """Stop metrics streaming"""
        self.streaming = False
        await self.broadcast({
            "type": "stream_stopped",
            "data": {}
        })

    async def metrics_collection_loop(self, target_service):
        """Background loop to collect and broadcast metrics"""
        while self.streaming:
            try:
                # Get current metrics
                current_metrics = self.monitoring_client._get_current_metrics(target_service)
                
                timestamp = datetime.now().isoformat()
                metrics_data = {
                    "timestamp": timestamp,
                    "metrics": current_metrics,
                    "baseline": self.baseline_metrics
                }
                
                # Store in history (keep last 100 points)
                self.metrics_history.append(metrics_data)
                if len(self.metrics_history) > 100:
                    self.metrics_history.pop(0)
                
                # Calculate changes from baseline
                changes = {}
                if self.baseline_metrics:
                    for metric, value in current_metrics.items():
                        if metric in self.baseline_metrics:
                            baseline_val = self.baseline_metrics[metric]
                            if baseline_val != 0:
                                change_percent = ((value - baseline_val) / baseline_val) * 100
                                changes[metric] = {
                                    "current": value,
                                    "baseline": baseline_val,
                                    "change_percent": change_percent
                                }
                
                # Broadcast to all clients
                await self.broadcast({
                    "type": "metrics_update",
                    "data": {
                        "timestamp": timestamp,
                        "metrics": current_metrics,
                        "changes": changes
                    }
                })
                
                # Wait before next collection
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logging.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def capture_baseline(self, target_service):
        """Capture baseline metrics"""
        self.baseline_metrics = self.monitoring_client.capture_baseline(target_service)
        
        await self.broadcast({
            "type": "baseline_captured",
            "data": {
                "service": target_service,
                "baseline": self.baseline_metrics,
                "timestamp": datetime.now().isoformat()
            }
        })

    def start_experiment(self, experiment):
        """Called when an experiment starts"""
        self.experiment_status.update({
            "running": True,
            "name": experiment["name"],
            "start_time": datetime.now().isoformat(),
            "duration": experiment.get("duration", 0),
            "target_service": experiment["target"]["service"]
        })
        
        # Send to all clients (use asyncio.create_task for async broadcast)
        asyncio.create_task(self.broadcast({
            "type": "experiment_started",
            "data": self.experiment_status
        }))

    def stop_experiment(self, results=None):
        """Called when an experiment stops"""
        self.experiment_status.update({
            "running": False,
            "name": None,
            "start_time": None,
            "duration": 0,
            "target_service": None
        })
        
        asyncio.create_task(self.broadcast({
            "type": "experiment_stopped",
            "data": {"results": results}
        }))

    async def start_server(self):
        """Start the WebSocket server"""
        logging.info(f"Starting dashboard server on {self.host}:{self.port}")
        
        try:
            server = await websockets.serve(
                self.client_handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            logging.info(f"Dashboard server started at ws://{self.host}:{self.port}")
            return server
        except Exception as e:
            logging.error(f"Failed to start dashboard server: {e}")
            raise

    def run_server(self):
        """Run the server in a separate thread"""
        def start_event_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server = loop.run_until_complete(self.start_server())
            loop.run_until_complete(server.wait_closed())
        
        thread = threading.Thread(target=start_event_loop, daemon=True)
        thread.start()
        return thread


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    server = DashboardServer()
    
    async def main():
        await server.start_server()
        # Keep the server running
        await asyncio.Future()  # Run forever
    
    asyncio.run(main())