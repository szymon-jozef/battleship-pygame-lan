import time
from threading import Thread

from battleship_pygame_lan.game_manager import GameManager, GuiEvent
from battleship_pygame_lan.network import NetworkServer, ReadyType


def test_game_manager() -> None:
    TEST_IP = "127.0.0.1"
    TEST_PORT = 6769

    server = NetworkServer(server_ip=TEST_IP)
    server.ADDR = (TEST_IP, TEST_PORT)

    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    player_name = "Morbius"
    game_manager = GameManager(player_name, server_ip=TEST_IP)

    game_manager.network_client.ADDR = (TEST_IP, TEST_PORT)
    game_manager.connect()
    time.sleep(0.1)

    assert game_manager.network_client.connected is True
    assert len(server.players) == 1
    assert server.players[0].player_name == "Morbius"

    game_manager.network_client.disconnect()
    time.sleep(0.1)

    assert len(server.players) == 0
    time.sleep(0.1)


def test_full_game_flow() -> None:
    TEST_IP = "127.0.0.1"
    TEST_PORT = 6770

    server = NetworkServer(server_ip=TEST_IP)
    server.ADDR = (TEST_IP, TEST_PORT)
    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    gm_morbius = GameManager("Morbius", server_ip=TEST_IP)
    gm_venom = GameManager("Venom", server_ip=TEST_IP)

    gm_morbius.network_client.ADDR = (TEST_IP, TEST_PORT)
    gm_venom.network_client.ADDR = (TEST_IP, TEST_PORT)

    gm_morbius.connect()
    gm_venom.connect()
    time.sleep(0.1)

    assert len(server.players) == 2

    gm_morbius.handle_response()
    gm_venom.handle_response()

    gm_morbius.network_client.ready(ReadyType.LOBBY)
    gm_venom.network_client.ready(ReadyType.LOBBY)
    time.sleep(0.1)

    gm_morbius.handle_response()
    gm_venom.handle_response()

    gm_morbius.network_client.ready(ReadyType.SHIP_PLACED)
    gm_venom.network_client.ready(ReadyType.SHIP_PLACED)
    time.sleep(0.1)

    gm_morbius.handle_response()
    gm_venom.handle_response()

    if gm_morbius.network_client.is_my_turn:
        active_gm, passive_gm = gm_morbius, gm_venom
    else:
        active_gm, passive_gm = gm_venom, gm_morbius

    active_gm.shoot(0, 0)
    time.sleep(0.1)

    passive_gm.handle_response()
    time.sleep(0.1)

    active_gm.handle_response()

    assert not active_gm.gui_events_queue.empty(), "GUI queue is empty!"

    gui_event = active_gm.gui_events_queue.get()
    assert gui_event in [GuiEvent.ShotHit, GuiEvent.ShotMissed], (
        f"Expected Hit or Miss, got {gui_event}"
    )

    gm_morbius.network_client.disconnect()
    gm_venom.network_client.disconnect()
    time.sleep(0.1)

    assert len(server.players) == 0
