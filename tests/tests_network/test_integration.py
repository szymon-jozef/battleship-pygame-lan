import time
from threading import Thread

from battleship_pygame_lan.logic import ShotResult
from battleship_pygame_lan.network import (
    GameState,
    NetworkClient,
    NetworkServer,
    PayloadTypes,
    ReadyType,
)


def test_client_server_connection_and_ready_flow() -> None:
    # TODO keep this test updated
    TEST_IP = "127.0.0.1"
    RANDOM_PORT = 0

    # SETUP
    server = NetworkServer(server_ip=TEST_IP)
    server.ADDR = (TEST_IP, RANDOM_PORT)

    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()

    time.sleep(0.1)

    TEST_PORT = server.server.getsockname()[1]  # get opened port

    client1_name = "Morbius"
    client1 = NetworkClient(player_name=client1_name, server_ip=TEST_IP)
    client1.ADDR = (TEST_IP, TEST_PORT)
    client1.connect()

    client2_name = "Spider-Mid"
    client2 = NetworkClient(player_name=client2_name, server_ip=TEST_IP)
    client2.ADDR = (TEST_IP, TEST_PORT)
    client2.connect()

    time.sleep(0.1)

    # test if players know their enemies
    assert client1.enemy_name == client2_name
    assert client2.enemy_name == client1_name

    time.sleep(0.1)

    assert len(server.players) == 2
    assert server.players[0].addr == client1.client.getsockname()
    assert server.players[1].addr == client2.client.getsockname()

    # both players are in the lobby and they press ready button
    client1.ready("Morbius", ReadyType.LOBBY)
    client2.ready("Spider-Mid", ReadyType.LOBBY)

    time.sleep(0.1)

    # both players have time to place their ships
    assert server.current_game_state == GameState.SHIP_PLACEMENT

    assert client1.current_game_state == GameState.SHIP_PLACEMENT
    assert client2.current_game_state == GameState.SHIP_PLACEMENT

    # both players placed their ships
    client1.ready(client1_name, ReadyType.SHIP_PLACED)
    client2.ready(client2_name, ReadyType.SHIP_PLACED)

    time.sleep(0.1)

    # WAR TEST
    assert server.current_game_state == GameState.WAR

    assert client1.current_game_state == GameState.WAR
    assert client2.current_game_state == GameState.WAR

    time.sleep(0.1)

    assert client1.is_my_turn is True
    assert client2.is_my_turn is False

    while not client1.message_queue.empty():
        client1.message_queue.get()
    while not client2.message_queue.empty():
        client2.message_queue.get()

    # morbius attacks!
    client1.send_attack_info(1, 1, client1_name, client2_name)
    time.sleep(0.1)

    # spider mid responds
    attack_event = client2.message_queue.get(timeout=1.0)
    assert attack_event.get("type") == PayloadTypes.ATTACK.value
    assert attack_event.get("row") == 1
    assert attack_event.get("column") == 1

    client2.send_shot_result(
        1, 1, ShotResult.Miss, sender=client2_name, receiver=client1_name
    )
    time.sleep(0.1)

    # morbius gets his response
    result_event = client1.message_queue.get(timeout=1.0)
    assert result_event.get("type") == PayloadTypes.SHOT_RESULT.value
    assert result_event.get("result") == ShotResult.Miss.name

    # if above works then they can communicate about war
    turn_event = client1.message_queue.get(timeout=1.0)
    assert turn_event.get("type") == PayloadTypes.CHANGE_TURN.value
    # now it's spider-mid turn

    assert client1.is_my_turn is False
    assert client2.is_my_turn is True

    # spider-mid losses as he's MID!!!
    client2.end(client2.player_name)

    time.sleep(0.1)

    assert server.current_game_state == GameState.FINISH

    # both players disconnect
    client1.disconnect()
    client2.disconnect()

    time.sleep(0.1)

    assert len(server.players) == 0

    # close the server
    server.stop()
