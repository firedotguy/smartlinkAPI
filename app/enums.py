from enum import Enum, IntEnum

from aenum import MultiValueEnum

# class InventoryCategoryType(Enum):
#     OTHER = 0
#     COMMUTATION = 1
#     ROUTER = 2
#     SPLITTER = 4
#     ODF = 7
#     ARBITARY_DEVICE = 16


class Role(Enum):
    cableman = 17
    admin = 1
    admin2 = 21
    insider = 26
    operator = 8
    marketing = 5
    ravshan_aka = 10
    ravshan_magistral = 19
    repairer = 24
    repairer_magistral = 27
    welder = 14  # сварщик
    installer = 13
    black_list = 11


class ActionType(Enum):
    login = "login"
    get_customer = "customer_view"
    get_building = "building_view"
    get_task = "task_view"
    get_ont = "ont_view"
    search = "search"
    ont_catv_toggle = "ont_toggle_catv"
    ont_rewrite_sn = "ont_rewrite_sn"
    ont_rewrite_mac = "ont_rewrite_mac"


class AddataCategories(Enum):
    cable_line = 2
    radio = 6
    house = 7
    device = 8  # коммутатор
    mediaconverter = 9
    system_device = 10
    tariff = 12
    service = 13
    node = 14
    switch = 15  # odf # !
    vlan = 16
    task = 17
    transport = 18
    advert = 19
    custom_device = 20
    trader = 21
    splitter = 23
    owner = 24
    tmc = 25  # !
    cable_duct = 26
    cable_ = 27  # !
    customer = 28
    key = 29
    inventory_name = 30  # !
    address = 40
    inventory = 48
    map_object = 102
    employee = 999


class AttachObjectType(Enum):
    additional_field = "additional_field"
    cable_line = "cable_line"
    customer = "customer"
    node = "node"
    task = "task"
    task_comment = "task_comment"
    inventory = "inventory"


class ItemLocation(Enum):
    storage = "storage"
    employee = "employee"
    customer = "customer"
    node = "node"
    task = "task"


class CustomerStatus(MultiValueEnum):
    inactive = 0, "Стоп"
    pause = 1, "Пауза"
    active = 2, "Активен"


class TariffType(Enum):
    base = "base"  # priced
    promo = "promo"  # free
    sale = "sale"  # % sale
    none = "none"  # no price/sale


class BuildingType(MultiValueEnum):
    multiflat = 1, 5, 7  # многоквартирные дома, ОШ многоквартирные дома, Джалал-А многоквартирные дома
    private = 2, 4  # частный сектор, ОШ частные дома
    office = 3  # офисное здание
    ravshan = 6  # Ош сеть А.Равшана
    new = 8  # Новостройки


class ItemType(MultiValueEnum):
    cable = "7ca47c6c-2384-47b4-805e-770ad0c6a695", 47
    olt = "9e8fb519-f26b-4452-8bd0-c8ebfe6eee89", 1
    edfa = "225fb13f-0335-4203-a479-6f210e51e64f", 39
    ont = "c7d54c9d-1b9a-4262-94c8-f353336630e1", 9
    clamp = "b641211a-4307-4dc7-aa21-9ecc83b556fe", 42  # зажим
    commutator = "486c7c6a-2748-4bea-9e15-c06f4ed8633b", 2, 6, 37
    coupling = "66638d77-0c99-42e1-a5ba-4d43ba31feb2", 46  # муфта
    odf = "7b8d762a-302a-4386-affe-09a927bc9cff", 8
    patchcord = "71519a2f-0808-4c2b-8776-5f8043cbc4a4", 17
    other = "17c40585-dca8-40ed-8ded-5673cba2dcea", 43
    junction = "3bdffaa5-3e68-453f-9bbd-8de2a76701da", 48  # распред коробка
    router = "565c435b-8514-4fb2-b752-e0d59a21139d", 49
    splitter = "a802f74e-2cf7-43e3-90b9-00255b03dc4d", 7
    smart_home = "6af4368b-77c0-4fae-a136-19a7f9dc757e", 41
    cisco = "9b78cb0d-55f5-405e-9dad-e64da86e5c1d"
    cambium = "c3b4836f-18f2-4d83-a2cc-dea043a57823"


class TaskType(IntEnum):
    repair = 37
    repair_ravshan = 53
    repair_magistral = 38
    inactive = 46
    uninstall = 60
    magistral = 48


# class OntBatteryStatus(Enum):
#     not_supported = 0
#     charge = 1
#     discharge = 2
#     holding = 3
#     invlid = 4
#     unknown = -1


class OntLastDownCause(Enum):
    LOS = 1
    LOSi = 2
    LOFi = 3
    SFI = 4
    LOAI = 5
    LOAMI = 6
    deactivate_fail = 7
    deactivate_success = 8
    reset = 9
    re_register = 10
    pop_up_fail = 11
    dying_gasp = 13
    LOKI = 15
    ring = 18
    optical = 30
    command_reset = 31
    button_reset = 32
    software_reset = 33
    broadcast_attack = 34
    operator_check_fail = 35
    rogue = 37
    invalid = -1


class EthDuplexMode(MultiValueEnum):
    half = 1, 4
    full = 2, 5
    autoneg = 3
    invalid = -1


# class GroupLocation(Enum):
#     ravshan = "ravshan"
#     osh = "Юг"
#     bishkek = "север"
#     tokmok = "Токмок"
#     uzgen = "Узген"


# class HouseType(Enum):
#     multiflat = "многоэтажный"
#     private = "частный"
