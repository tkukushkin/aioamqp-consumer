import asyncio

import pytest

from aioamqp_consumer.base_middlewares import Eoq
from aioamqp_consumer.message import Message, MessageAlreadyResolved
from aioamqp_consumer.middlewares import to_json, ProcessBulk
from tests.utils import Arg, collect_queue, future, make_queue


pytestmark = pytest.mark.asyncio


async def test_to_json(mocker):
    # arrange
    message1 = Message(
        body='{"hello": "world"}',
        channel=mocker.sentinel.channel,
        envelope=mocker.sentinel.envelope,
        properties=mocker.sentinel.properties,
    )
    message2 = Message(
        body='invalid json',
        channel=mocker.sentinel.channel,
        envelope=mocker.sentinel.envelope,
        properties=mocker.sentinel.properties,
    )
    mocker.patch.object(message2, 'reject', return_value=future())

    input_queue = make_queue([message1, message2, Eoq()])
    output_queue = asyncio.Queue()

    # act
    await to_json.run(input_queue, output_queue)

    # assert
    message_arg = Arg()
    assert collect_queue(output_queue) == [message_arg, Eoq()]
    assert message_arg.value.body == {'hello': 'world'}

    message2.reject.assert_called_once_with(requeue=False)


class TestProcessBulk:

    async def test_run__success__ack_all_messages(self, mocker):
        # arrange
        message1 = Message(
            body='message1',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message1, 'ack', return_value=future())
        message2 = Message(
            body='message2',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message2, 'ack', return_value=future(exception=MessageAlreadyResolved()))

        input_queue = make_queue([[message1, message2], Eoq()])
        output_queue = asyncio.Queue()

        # act
        await ProcessBulk(lambda messages: future(None)).run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [None, Eoq()]

        message1.ack.assert_called_once_with()
        message2.ack.assert_called_once_with()

    async def test_run__func_raised_exception__reject_all_messages(self, mocker):
        # arrange
        message1 = Message(
            body='message1',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message1, 'reject', return_value=future())
        message2 = Message(
            body='message2',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message2, 'reject', return_value=future(exception=MessageAlreadyResolved()))

        input_queue = make_queue([[message1, message2], Eoq()])
        output_queue = asyncio.Queue()

        # act
        await ProcessBulk(lambda messages: future(exception=Exception())).run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [None, Eoq()]

        message1.reject.assert_called_once_with()
        message2.reject.assert_called_once_with()