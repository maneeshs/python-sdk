import grpc
from concurrent import futures
from google.protobuf.any_pb2 import Any as GrpcAny
from google.protobuf import empty_pb2
from dapr.proto import api_service_v1, common_v1, api_v1


class FakeDaprSidecar(api_service_v1.DaprServicer):
    def __init__(self):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        api_service_v1.add_DaprServicer_to_server(self, self._server)
        self.store = {}

    def start(self, port: int = 8080):
        self._server.add_insecure_port(f'[::]:{port}')
        self._server.start()

    def stop(self):
        self._server.stop(None)

    def InvokeService(self, request, context) -> common_v1.InvokeResponse:
        headers = ()
        trailers = ()

        for k, v in context.invocation_metadata():
            headers = headers + (('h' + k, v), )
            trailers = trailers + (('t' + k, v), )

        resp = GrpcAny()
        content_type = ''

        if request.message.method == 'bytes':
            resp.value = request.message.data.value
            content_type = request.message.content_type
        else:
            resp = request.message.data

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)

        return common_v1.InvokeResponse(data=resp, content_type=content_type)

    def InvokeBinding(self, request, context) -> api_v1.InvokeBindingResponse:
        headers = ()
        trailers = ()

        for k, v in request.metadata.items():
            headers = headers + (('h' + k, v), )
            trailers = trailers + (('t' + k, v), )

        resp_data = b'INVALID'
        metadata = {}

        if request.operation == 'create':
            resp_data = request.data
            metadata = request.metadata

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)

        return api_v1.InvokeBindingResponse(data=resp_data, metadata=metadata)

    def PublishEvent(self, request, context):
        headers = ()
        trailers = ()
        if request.topic:
            headers = headers + (('htopic', request.topic),)
            trailers = trailers + (('ttopic', request.topic),)
        if request.data:
            headers = headers + (('hdata', request.data), )
            trailers = trailers + (('hdata', request.data), )

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)
        return empty_pb2.Empty()

    def SaveState(self, request, context):
        headers = ()
        trailers = ()
        for state in request.states:
            self.store[state.key] = state.value

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)
        return empty_pb2.Empty()

    def GetState(self, request, context):
        key = request.key
        if key not in self.store:
            return empty_pb2.Empty()
        else:
            return api_v1.GetStateResponse(data=self.store[key], etag="")

    def DeleteState(self, request, context):
        headers = ()
        trailers = ()
        key = request.key
        if key in self.store:
            del self.store[key]

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)
        return empty_pb2.Empty()

    def GetSecret(self, request, context) -> api_v1.GetSecretResponse:
        headers = ()
        trailers = ()

        key = request.key

        headers = headers + (('keyh', key), )
        trailers = trailers + (('keyt', key), )

        resp = {key: "val"}

        context.send_initial_metadata(headers)
        context.set_trailing_metadata(trailers)

        return api_v1.GetSecretResponse(data=resp)
