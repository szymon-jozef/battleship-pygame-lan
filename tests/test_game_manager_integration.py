import time
from threading import Thread

from battleship_pygame_lan.game_manager import GameManager, GuiEvent
from battleship_pygame_lan.logic import ShipType
from battleship_pygame_lan.network import GameState, NetworkServer, ReadyType


def test_game_manager() -> None:
    TEST_IP = "127.0.0.1"
    RANDOM_PORT = 0

    server = NetworkServer(server_ip=TEST_IP)
    server.ADDR = (TEST_IP, RANDOM_PORT)

    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.1)
    TEST_PORT = server.server.getsockname()[1]

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
    RANDOM_PORT = 0

    server = NetworkServer(server_ip=TEST_IP)
    server.ADDR = (TEST_IP, RANDOM_PORT)
    server_thread = Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.1)
    TEST_PORT = server.server.getsockname()[1]

    # setup players
    gm_morbius = GameManager("Morbius", server_ip=TEST_IP)
    gm_venom = GameManager("Venom", server_ip=TEST_IP)

    gm_morbius.network_client.ADDR = (TEST_IP, TEST_PORT)
    gm_venom.network_client.ADDR = (TEST_IP, TEST_PORT)

    # connect
    gm_morbius.connect()
    gm_venom.connect()
    time.sleep(0.1)

    assert len(server.players) == 2

    gm_morbius.handle_response()
    gm_venom.handle_response()

    # players are in some kind of lobby now
    assert server.current_game_state == GameState.LOBBY

    # both of them hit ready
    gm_morbius.network_client.ready(ReadyType.LOBBY)
    gm_venom.network_client.ready(ReadyType.LOBBY)
    time.sleep(0.1)

    gm_morbius.handle_response()
    gm_venom.handle_response()

    assert gm_morbius.get_game_state == GameState.SHIP_PLACEMENT
    assert gm_venom.get_game_state == GameState.SHIP_PLACEMENT

    # they place their ships
    gm_morbius.place_ship(ShipType.OneMaster, 5, 5)
    gm_venom.place_ship(ShipType.TwoMaster, 2, 2)

    # they say that they placed them
    gm_morbius.network_client.ready(ReadyType.SHIP_PLACED)
    gm_venom.network_client.ready(ReadyType.SHIP_PLACED)
    time.sleep(0.1)

    gm_morbius.handle_response()
    gm_venom.handle_response()

    assert gm_morbius.get_game_state == GameState.WAR
    assert gm_venom.get_game_state == GameState.WAR

    # they shoot at each other

    if gm_morbius.network_client.is_my_turn:
        active_gm, passive_gm = gm_morbius, gm_venom
    else:
        active_gm, passive_gm = gm_venom, gm_morbius

    # this should be a miss
    active_gm.shoot(0, 0)
    time.sleep(0.1)

    passive_gm.handle_response()
    time.sleep(0.1)

    active_gm.handle_response()

    assert not active_gm.gui_events_queue.empty(), "GUI queue is empty!"

    gui_event = active_gm.gui_events_queue.get()
    assert gui_event == GuiEvent.ShotMissed, f"Expected Hit or Miss, got {gui_event}"

    # now let's hit something (the turn has changed)
    passive_gm.shoot(5, 5)

    time.sleep(0.1)

    active_gm.handle_response()
    time.sleep(0.1)

    passive_gm.handle_response()

    assert not passive_gm.gui_events_queue.empty(), "GUI queue is empty!"

    # this should be a hit
    gui_event = passive_gm.gui_events_queue.get()
    assert gui_event == GuiEvent.ShotHit, f"Expected Hit or Miss, got {gui_event}"

    # morbius lost
    # TODO! check for this

    gm_morbius.network_client.disconnect()
    gm_venom.network_client.disconnect()
    time.sleep(0.1)

    assert len(server.players) == 0
