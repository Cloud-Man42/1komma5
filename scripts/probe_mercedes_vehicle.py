"""Probe Mercedes REST vehicleattributes from production tokens."""
import asyncio
import uuid

from energy_core.config import get_settings
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.mercedes.provider import MercedesProvider


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    secrets = SecretBox.from_settings()

    async with factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        row = await VehicleProviderRepository(session, secret_box=secrets).get_for_site(site.id)
        assert row is not None
        bundle = VehicleProviderRepository(session, secret_box=secrets).load_token_bundle(row)
        assert bundle is not None
        provider = MercedesProvider(region=row.region, device_guid=row.device_guid or str(uuid.uuid4()), token_bundle=bundle)
        try:
            await provider._discover_vehicles()
            for vid, state in provider._vehicles.items():
                vin = state.vin or vid
                print("VEHICLE", vin)
                try:
                    payload = await provider._rest.get_vehicle_attributes(vin)
                    print("ATTR_BYTES", len(payload), "HEAD", payload[:16].hex())
                    if payload[:1] in (b"{", b"["):
                        print("ATTR_JSON", payload[:200])
                    from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2

                    vep = vehicle_events_pb2.VEPUpdate()
                    try:
                        vep.ParseFromString(payload)
                        print("VEP_RAW", vep)
                    except Exception as exc:
                        print("VEP_PARSE_ERR", exc)
                    push = vehicle_events_pb2.PushMessage()
                    try:
                        push.ParseFromString(payload)
                        print("PUSH_RAW", push)
                    except Exception as exc:
                        print("PUSH_PARSE_ERR", exc)
                    msg = provider._decoder.decode_vep_update(payload)
                    print("VEP", msg)
                    if msg is None or not msg.attributes:
                        msg2 = provider._decoder.decode(payload)
                        print("PUSH", msg2)
                except Exception as exc:
                    print("ATTR_ERROR", type(exc).__name__, exc)
            states = await provider.sync_from_rest()
            print("SYNC_STATES", [(s.vin, s.state_of_charge_percent, s.is_plugged_in, s.is_charging) for s in states])
        finally:
            await provider.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
