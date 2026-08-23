"""Central EV charger vendor catalog — data-driven integration profiles."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.chargers.framework.models import (
    ChargerCapabilities,
    ChargerIntegrationMethodDefinition,
    ChargerManufacturerDefinition,
    ChargerModelDefinition,
    ConnectionFieldDefinition,
    CredentialFieldDefinition,
    SupportLevel,
)

CHARGE_AMPS_CLOUD = "CHARGE_AMPS_CLOUD"
ZAPTEC_REST = "ZAPTEC_REST"
EASEE_CLOUD = "EASEE_CLOUD"
GOE_LOCAL_HTTP = "GOE_LOCAL_HTTP"
GOE_CLOUD = "GOE_CLOUD"
GOE_MQTT = "GOE_MQTT"
GOE_MODBUS = "GOE_MODBUS"
NEXBLUE_MODBUS = "NEXBLUE_MODBUS"
NEXBLUE_OCPP_16J = "NEXBLUE_OCPP_16J"
NEXBLUE_OCPP_201 = "NEXBLUE_OCPP_201"
GARO_CONNECT = "GARO_CONNECT"
DEFA_CLOUD = "DEFA_CLOUD"
WALLBOX_CLOUD = "WALLBOX_CLOUD"
MYENERGI_CLOUD = "MYENERGI_CLOUD"
CTEK_CLOUD = "CTEK_CLOUD"
KEBA_REST = "KEBA_REST"
KEBA_MODBUS = "KEBA_MODBUS"
SCHNEIDER_MODBUS = "SCHNEIDER_MODBUS"
OCPP_16J = "OCPP_16J"
OCPP_201 = "OCPP_201"
EO_CLOUD = "EO_CLOUD"
OHME_CLOUD = "OHME_CLOUD"
HYPERVOLT_CLOUD = "HYPERVOLT_CLOUD"
ENUa_PLATFORM = "ENUa_PLATFORM"
AMINA_PARTNER = "AMINA_PARTNER"


def _caps(
    *,
    status: SupportLevel,
    current: bool = False,
    start_stop: bool = False,
    power: bool = False,
    energy: bool = False,
    session: bool = False,
    smart: bool = False,
    local: bool = False,
    cloud: bool = False,
    ocpp: bool = False,
    modbus: bool = False,
    min_a: float = 6.0,
    max_a: float = 16.0,
    phases: int = 3,
) -> ChargerCapabilities:
    return ChargerCapabilities(
        min_current_a=min_a,
        max_current_a=max_a,
        phases=phases,
        can_read_status=True,
        can_start_charging=start_stop,
        can_stop_charging=start_stop,
        can_read_power=power,
        can_read_energy=energy,
        can_read_session=session,
        can_read_actual_current=power or current,
        can_set_max_current=current,
        can_read_meter_values=power or energy,
        supports_dynamic_current=current,
        supports_local_control=local,
        supports_cloud_control=cloud,
        supports_ocpp=ocpp,
        supports_modbus=modbus,
        supports_smart_charging=smart and current and start_stop,
        supports_current_control=current,
        supports_remote_start_stop=start_stop,
        supports_power_reading=power,
    )


def _full_charge_amps() -> ChargerCapabilities:
    return _caps(
        status="FULL",
        current=True,
        start_stop=True,
        power=True,
        energy=True,
        session=True,
        smart=True,
        cloud=True,
    )


def _monitoring_only() -> ChargerCapabilities:
    return _caps(status="MONITORING_ONLY")


def _unsupported_caps() -> ChargerCapabilities:
    return ChargerCapabilities(can_read_status=False)


INTEGRATION_METHODS: dict[str, ChargerIntegrationMethodDefinition] = {
    CHARGE_AMPS_CLOUD: ChargerIntegrationMethodDefinition(
        id=CHARGE_AMPS_CLOUD,
        label="Charge Amps Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="FULL",
        cloud_dependent=True,
        documentation_url="https://eapi.charge.space/swagger/index.html",
        credential_fields=(
            CredentialFieldDefinition("api_key", "API-nyckel", "password"),
            CredentialFieldDefinition(
                "charger_id", "Laddbox-ID", help_text="Charge Amps charge point ID"
            ),
        ),
    ),
    ZAPTEC_REST: ChargerIntegrationMethodDefinition(
        id=ZAPTEC_REST,
        label="Zaptec REST API",
        protocol="REST",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
        documentation_url="https://docs.zaptec.com/",
        credential_fields=(
            CredentialFieldDefinition("account_id", "Zaptec-konto / installation ID"),
            CredentialFieldDefinition("api_key", "API-nyckel / token", "password"),
            CredentialFieldDefinition("charger_id", "Charger ID"),
        ),
    ),
    EASEE_CLOUD: ChargerIntegrationMethodDefinition(
        id=EASEE_CLOUD,
        label="Easee Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
        documentation_url="https://developer.easee.com/",
        credential_fields=(
            CredentialFieldDefinition("username", "Easee-användare"),
            CredentialFieldDefinition("password", "Lösenord", "password"),
            CredentialFieldDefinition("charger_id", "Charger ID"),
        ),
    ),
    GOE_LOCAL_HTTP: ChargerIntegrationMethodDefinition(
        id=GOE_LOCAL_HTTP,
        label="go-e Local HTTP API",
        protocol="LOCAL_HTTP",
        connection_type="LOCAL",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        documentation_url="https://github.com/goecharger/go-e-API-v2",
        connection_fields=(
            ConnectionFieldDefinition(
                "host", "IP / värdnamn", "hostname", placeholder="192.168.1.100"
            ),
            ConnectionFieldDefinition("port", "Port", "port", required=False, placeholder="80"),
        ),
        credential_fields=(
            CredentialFieldDefinition(
                "api_token", "API-token (valfritt)", "password", required=False
            ),
        ),
    ),
    GOE_CLOUD: ChargerIntegrationMethodDefinition(
        id=GOE_CLOUD,
        label="go-e Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        priority=2,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    GOE_MQTT: ChargerIntegrationMethodDefinition(
        id=GOE_MQTT,
        label="go-e MQTT",
        protocol="MQTT",
        connection_type="LOCAL",
        priority=3,
        implementation_status="UNSUPPORTED",
        connection_fields=(
            ConnectionFieldDefinition("host", "MQTT broker", "hostname"),
            ConnectionFieldDefinition("port", "Port", "port", placeholder="1883"),
            ConnectionFieldDefinition("topic", "Topic prefix"),
        ),
    ),
    GOE_MODBUS: ChargerIntegrationMethodDefinition(
        id=GOE_MODBUS,
        label="go-e Modbus TCP",
        protocol="MODBUS_TCP",
        connection_type="LOCAL",
        priority=4,
        implementation_status="UNSUPPORTED",
        connection_fields=(
            ConnectionFieldDefinition("host", "Modbus host", "hostname"),
            ConnectionFieldDefinition("port", "Port", "port", placeholder="502"),
            ConnectionFieldDefinition("unit_id", "Unit ID", "number", placeholder="1"),
        ),
    ),
    OCPP_16J: ChargerIntegrationMethodDefinition(
        id=OCPP_16J,
        label="OCPP 1.6J (EMIC CSMS)",
        protocol="OCPP_1_6J",
        connection_type="OCPP",
        recommended=True,
        priority=10,
        implementation_status="UNSUPPORTED",
        connection_fields=(
            ConnectionFieldDefinition(
                "charge_point_id",
                "Charge Point ID",
                help_text="ID som laddboxen ansluter med till EMIC OCPP",
            ),
        ),
        credential_fields=(
            CredentialFieldDefinition(
                "password", "OCPP-lösenord (valfritt)", "password", required=False
            ),
        ),
    ),
    OCPP_201: ChargerIntegrationMethodDefinition(
        id=OCPP_201,
        label="OCPP 2.0.1 (EMIC CSMS)",
        protocol="OCPP_2_0_1",
        connection_type="OCPP",
        priority=11,
        implementation_status="UNSUPPORTED",
        connection_fields=(ConnectionFieldDefinition("charge_point_id", "Charge Point ID"),),
    ),
    KEBA_REST: ChargerIntegrationMethodDefinition(
        id=KEBA_REST,
        label="KEBA REST API",
        protocol="REST",
        connection_type="LOCAL",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        documentation_url="https://www.keba.com/",
        connection_fields=(ConnectionFieldDefinition("host", "IP / värdnamn", "hostname"),),
    ),
    KEBA_MODBUS: ChargerIntegrationMethodDefinition(
        id=KEBA_MODBUS,
        label="KEBA Modbus TCP",
        protocol="MODBUS_TCP",
        connection_type="LOCAL",
        priority=2,
        implementation_status="UNSUPPORTED",
        connection_fields=(
            ConnectionFieldDefinition("host", "Modbus host", "hostname"),
            ConnectionFieldDefinition("port", "Port", "port", placeholder="502"),
            ConnectionFieldDefinition("unit_id", "Unit ID", "number", placeholder="1"),
        ),
    ),
    SCHNEIDER_MODBUS: ChargerIntegrationMethodDefinition(
        id=SCHNEIDER_MODBUS,
        label="Schneider Modbus TCP",
        protocol="MODBUS_TCP",
        connection_type="LOCAL",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
    ),
    WALLBOX_CLOUD: ChargerIntegrationMethodDefinition(
        id=WALLBOX_CLOUD,
        label="Wallbox Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    MYENERGI_CLOUD: ChargerIntegrationMethodDefinition(
        id=MYENERGI_CLOUD,
        label="myenergi Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    DEFA_CLOUD: ChargerIntegrationMethodDefinition(
        id=DEFA_CLOUD,
        label="DEFA Cloud / backend",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    GARO_CONNECT: ChargerIntegrationMethodDefinition(
        id=GARO_CONNECT,
        label="GARO Connect / backend",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    NEXBLUE_MODBUS: ChargerIntegrationMethodDefinition(
        id=NEXBLUE_MODBUS,
        label="NexBlue Modbus TCP",
        protocol="MODBUS_TCP",
        connection_type="LOCAL",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
    ),
    NEXBLUE_OCPP_16J: ChargerIntegrationMethodDefinition(
        id=NEXBLUE_OCPP_16J,
        label="NexBlue OCPP 1.6J",
        protocol="OCPP_1_6J",
        connection_type="OCPP",
        priority=2,
        implementation_status="UNSUPPORTED",
    ),
    NEXBLUE_OCPP_201: ChargerIntegrationMethodDefinition(
        id=NEXBLUE_OCPP_201,
        label="NexBlue OCPP 2.0.1",
        protocol="OCPP_2_0_1",
        connection_type="OCPP",
        priority=3,
        implementation_status="UNSUPPORTED",
    ),
    CTEK_CLOUD: ChargerIntegrationMethodDefinition(
        id=CTEK_CLOUD,
        label="CTEK Cloud / backend",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    EO_CLOUD: ChargerIntegrationMethodDefinition(
        id=EO_CLOUD,
        label="EO Cloud / backend",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    OHME_CLOUD: ChargerIntegrationMethodDefinition(
        id=OHME_CLOUD,
        label="Ohme Cloud",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    HYPERVOLT_CLOUD: ChargerIntegrationMethodDefinition(
        id=HYPERVOLT_CLOUD,
        label="Hypervolt Cloud API",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    ENUa_PLATFORM: ChargerIntegrationMethodDefinition(
        id=ENUa_PLATFORM,
        label="Enua platform / backend",
        protocol="CLOUD_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
    AMINA_PARTNER: ChargerIntegrationMethodDefinition(
        id=AMINA_PARTNER,
        label="Amina partner / EMS integration",
        protocol="PARTNER_API",
        connection_type="CLOUD",
        recommended=True,
        priority=1,
        implementation_status="UNSUPPORTED",
        cloud_dependent=True,
    ),
}


def _model(
    manufacturer_id: str,
    model_id: str,
    name: str,
    *,
    methods: tuple[str, ...],
    status: SupportLevel,
    caps: ChargerCapabilities | None = None,
    protocols: tuple[str, ...] = ("CLOUD_API",),
    docs: str | None = None,
) -> ChargerModelDefinition:
    return ChargerModelDefinition(
        id=model_id,
        manufacturer_id=manufacturer_id,
        name=name,
        supported_protocols=protocols,  # type: ignore[arg-type]
        capabilities=caps or _unsupported_caps(),
        integration_methods=methods,
        status=status,
        documentation_url=docs,
    )


MANUFACTURERS: tuple[ChargerManufacturerDefinition, ...] = (
    ChargerManufacturerDefinition(
        id="charge-amps",
        name="Charge Amps",
        models=(
            _model(
                "charge-amps",
                "halo",
                "Halo",
                methods=(CHARGE_AMPS_CLOUD,),
                status="FULL",
                caps=_full_charge_amps(),
            ),
            _model(
                "charge-amps",
                "aura",
                "Aura",
                methods=(CHARGE_AMPS_CLOUD, OCPP_16J),
                status="PARTIAL",
                caps=_full_charge_amps(),
            ),
            _model(
                "charge-amps",
                "dawn",
                "Dawn",
                methods=(CHARGE_AMPS_CLOUD, OCPP_16J),
                status="PARTIAL",
                caps=_full_charge_amps(),
            ),
            _model(
                "charge-amps",
                "dawn-pro",
                "Dawn Professional",
                methods=(CHARGE_AMPS_CLOUD, OCPP_16J),
                status="PARTIAL",
                caps=_full_charge_amps(),
            ),
            _model(
                "charge-amps",
                "luna",
                "Luna",
                methods=(CHARGE_AMPS_CLOUD, OCPP_16J),
                status="PARTIAL",
                caps=_full_charge_amps(),
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="zaptec",
        name="Zaptec",
        models=(
            _model("zaptec", "go", "Go", methods=(ZAPTEC_REST, OCPP_16J), status="UNSUPPORTED"),
            _model("zaptec", "go-2", "Go 2", methods=(ZAPTEC_REST, OCPP_16J), status="UNSUPPORTED"),
            _model("zaptec", "pro", "Pro", methods=(ZAPTEC_REST, OCPP_16J), status="UNSUPPORTED"),
            _model(
                "zaptec",
                "pro-mid",
                "Pro MID",
                methods=(ZAPTEC_REST, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="easee",
        name="Easee",
        models=(
            _model(
                "easee",
                "charge-up",
                "Charge Up",
                methods=(EASEE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "easee",
                "charge-core",
                "Charge Core",
                methods=(EASEE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "easee",
                "charge-max",
                "Charge Max",
                methods=(EASEE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "easee",
                "charge-pro",
                "Charge Pro",
                methods=(EASEE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="go-e",
        name="go-e",
        models=(
            _model(
                "go-e",
                "gemini",
                "Gemini",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "go-e",
                "gemini-2",
                "Gemini 2.0",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "go-e",
                "gemini-flex",
                "Gemini Flex",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "go-e",
                "gemini-flex-2",
                "Gemini Flex 2.0",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "go-e",
                "pro",
                "PRO",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "go-e",
                "core",
                "CORE",
                methods=(GOE_LOCAL_HTTP, GOE_MODBUS, GOE_MQTT, GOE_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="nexblue",
        name="NexBlue",
        models=(
            _model(
                "nexblue",
                "edge",
                "Edge",
                methods=(NEXBLUE_MODBUS, NEXBLUE_OCPP_16J, NEXBLUE_OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "nexblue",
                "edge-2",
                "Edge 2",
                methods=(NEXBLUE_MODBUS, NEXBLUE_OCPP_16J, NEXBLUE_OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "nexblue",
                "edge-max",
                "Edge Max",
                methods=(NEXBLUE_MODBUS, NEXBLUE_OCPP_16J, NEXBLUE_OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "nexblue",
                "delta",
                "Delta",
                methods=(NEXBLUE_MODBUS, NEXBLUE_OCPP_16J, NEXBLUE_OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "nexblue",
                "delta-max",
                "Delta Max",
                methods=(NEXBLUE_MODBUS, NEXBLUE_OCPP_16J, NEXBLUE_OCPP_201),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="garo",
        name="GARO",
        models=(
            _model(
                "garo",
                "entity-home",
                "Entity Home",
                methods=(GARO_CONNECT, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "garo",
                "entity-compact",
                "Entity Compact",
                methods=(GARO_CONNECT, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "garo",
                "entity-pro",
                "Entity Pro",
                methods=(GARO_CONNECT, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "garo",
                "entity-pro-mid",
                "Entity Pro MID",
                methods=(GARO_CONNECT, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="defa",
        name="DEFA",
        models=(
            _model("defa", "power", "Power", methods=(DEFA_CLOUD, OCPP_201), status="UNSUPPORTED"),
            _model(
                "defa",
                "power-home",
                "Power Home",
                methods=(DEFA_CLOUD, OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "defa", "power-s", "Power S", methods=(DEFA_CLOUD, OCPP_201), status="UNSUPPORTED"
            ),
            _model(
                "defa",
                "power-facility",
                "Power Facility",
                methods=(DEFA_CLOUD, OCPP_201),
                status="UNSUPPORTED",
            ),
            _model(
                "defa", "power-up", "Power Up", methods=(DEFA_CLOUD, OCPP_201), status="UNSUPPORTED"
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="wallbox",
        name="Wallbox",
        models=(
            _model(
                "wallbox",
                "pulsar-max",
                "Pulsar Max",
                methods=(WALLBOX_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "wallbox",
                "pulsar-plus",
                "Pulsar Plus",
                methods=(WALLBOX_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "wallbox",
                "copper-sb",
                "Copper SB",
                methods=(WALLBOX_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "wallbox",
                "commander",
                "Commander",
                methods=(WALLBOX_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="myenergi",
        name="myenergi",
        models=(
            _model(
                "myenergi",
                "zappi-v21",
                "Zappi v2.1",
                methods=(MYENERGI_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="tesla",
        name="Tesla",
        models=(
            _model(
                "tesla",
                "wall-connector-gen3",
                "Wall Connector Gen 3",
                methods=(OCPP_16J,),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="ctek",
        name="CTEK",
        models=(
            _model(
                "ctek",
                "chargestorm-connected-2",
                "Chargestorm Connected 2",
                methods=(CTEK_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "ctek", "njord-go", "Njord Go", methods=(CTEK_CLOUD, OCPP_16J), status="UNSUPPORTED"
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="abb",
        name="ABB",
        models=(_model("abb", "terra-ac", "Terra AC", methods=(OCPP_16J,), status="UNSUPPORTED"),),
    ),
    ChargerManufacturerDefinition(
        id="schneider",
        name="Schneider Electric",
        models=(
            _model(
                "schneider",
                "evlink-pro-ac",
                "EVlink Pro AC",
                methods=(SCHNEIDER_MODBUS, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="keba",
        name="KEBA",
        models=(
            _model(
                "keba",
                "kecontact-p30",
                "KeContact P30",
                methods=(KEBA_REST, KEBA_MODBUS, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "keba",
                "kecontact-p40",
                "KeContact P40",
                methods=(KEBA_REST, KEBA_MODBUS, OCPP_16J),
                status="UNSUPPORTED",
            ),
            _model(
                "keba",
                "kecontact-p40-pro",
                "KeContact P40 Pro",
                methods=(KEBA_REST, KEBA_MODBUS, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="alfen",
        name="Alfen",
        models=(
            _model(
                "alfen",
                "eve-single-pro-line",
                "Eve Single Pro-line",
                methods=(OCPP_16J,),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="mennekes",
        name="Mennekes",
        models=(
            _model(
                "mennekes",
                "amtron-professional",
                "AMTRON Professional",
                methods=(OCPP_16J,),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="autel",
        name="Autel",
        models=(
            _model(
                "autel",
                "maxicharger-ac",
                "MaxiCharger AC",
                methods=(OCPP_16J,),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="amina",
        name="Amina",
        models=(
            _model("amina", "amina-s", "Amina S", methods=(AMINA_PARTNER,), status="UNSUPPORTED"),
        ),
    ),
    ChargerManufacturerDefinition(
        id="eo-charging",
        name="EO Charging",
        models=(
            _model(
                "eo-charging",
                "mini-pro-3",
                "Mini Pro 3",
                methods=(EO_CLOUD, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="ohme",
        name="Ohme",
        models=(
            _model(
                "ohme", "home-pro", "Home Pro", methods=(OHME_CLOUD, OCPP_16J), status="UNSUPPORTED"
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="hypervolt",
        name="Hypervolt",
        models=(
            _model(
                "hypervolt", "home-3", "Home 3.0", methods=(HYPERVOLT_CLOUD,), status="UNSUPPORTED"
            ),
        ),
    ),
    ChargerManufacturerDefinition(
        id="enua",
        name="Enua",
        models=(
            _model(
                "enua", "charge", "Charge", methods=(ENUa_PLATFORM, OCPP_16J), status="UNSUPPORTED"
            ),
            _model(
                "enua",
                "wallmount",
                "Wallmount",
                methods=(ENUa_PLATFORM, OCPP_16J),
                status="UNSUPPORTED",
            ),
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class ChargerCatalog:
    manufacturers: tuple[ChargerManufacturerDefinition, ...]
    integration_methods: dict[str, ChargerIntegrationMethodDefinition]


_CATALOG = ChargerCatalog(manufacturers=MANUFACTURERS, integration_methods=INTEGRATION_METHODS)


def get_catalog() -> ChargerCatalog:
    return _CATALOG


def list_manufacturers() -> tuple[ChargerManufacturerDefinition, ...]:
    return _CATALOG.manufacturers


def get_manufacturer(manufacturer_id: str) -> ChargerManufacturerDefinition | None:
    for manufacturer in _CATALOG.manufacturers:
        if manufacturer.id == manufacturer_id:
            return manufacturer
    return None


def list_models(manufacturer_id: str) -> tuple[ChargerModelDefinition, ...]:
    manufacturer = get_manufacturer(manufacturer_id)
    if manufacturer is None:
        return ()
    return manufacturer.models


def get_model(manufacturer_id: str, model_id: str) -> ChargerModelDefinition | None:
    for model in list_models(manufacturer_id):
        if model.id == model_id:
            return model
    return None


def get_integration_method(method_id: str) -> ChargerIntegrationMethodDefinition | None:
    return _CATALOG.integration_methods.get(method_id)


def list_all_integration_methods() -> tuple[ChargerIntegrationMethodDefinition, ...]:
    return tuple(
        sorted(_CATALOG.integration_methods.values(), key=lambda item: (item.priority, item.label))
    )


def list_integration_methods(
    manufacturer_id: str, model_id: str
) -> tuple[ChargerIntegrationMethodDefinition, ...]:
    model = get_model(manufacturer_id, model_id)
    if model is None:
        return ()
    methods: list[ChargerIntegrationMethodDefinition] = []
    for method_id in model.integration_methods:
        method = get_integration_method(method_id)
        if method is not None:
            methods.append(method)
    return tuple(sorted(methods, key=lambda item: (item.priority, item.label)))


def feature_matrix_rows() -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    for manufacturer in _CATALOG.manufacturers:
        for model in manufacturer.models:
            caps = model.capabilities
            rows.append(
                {
                    "manufacturer": manufacturer.name,
                    "model": model.name,
                    "support": model.status,
                    "start_stop": caps.can_start_charging,
                    "current": caps.can_set_max_current,
                    "energy": caps.can_read_energy,
                    "session": caps.can_read_session,
                    "smart_charging": caps.supports_smart_charging,
                }
            )
    return rows


def validate_catalog() -> list[str]:
    """Return validation errors for catalog integrity."""
    errors: list[str] = []
    manufacturer_ids: set[str] = set()
    for manufacturer in _CATALOG.manufacturers:
        if manufacturer.id in manufacturer_ids:
            errors.append(f"Duplicate manufacturer id: {manufacturer.id}")
        manufacturer_ids.add(manufacturer.id)
        model_ids: set[str] = set()
        for model in manufacturer.models:
            if model.id in model_ids:
                errors.append(f"Duplicate model id {model.id} for {manufacturer.id}")
            model_ids.add(model.id)
            if model.manufacturer_id != manufacturer.id:
                errors.append(
                    f"Model {model.id} manufacturer_id mismatch: {model.manufacturer_id} != {manufacturer.id}"
                )
            for method_id in model.integration_methods:
                method = get_integration_method(method_id)
                if method is None:
                    errors.append(
                        f"Unknown integration method {method_id} on {manufacturer.id}/{model.id}"
                    )
            if model.status == "FULL" and not model.capabilities.supports_smart_charging:
                if (
                    model.capabilities.can_set_max_current
                    and model.capabilities.can_start_charging
                    or model.id == "halo"
                ):
                    pass
                else:
                    errors.append(
                        f"FULL model without smart charging caps: {manufacturer.id}/{model.id}"
                    )
    return errors
