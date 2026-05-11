from pydantic import BaseModel
from typing import List, Optional

class ContainerDetail(BaseModel):
    container_number: str = ""
    seal_number: str = ""
    type: str = ""             # e.g. 20' DRY VAN
    tare_weight: str = ""
    gross_weight: str = ""
    description: str = ""

class CargoDetails(BaseModel):
    bill_of_lading_number: str = ""
    shipper: str = ""
    consignee: str = ""
    notify_party: str = ""
    vessel: str = ""
    voyage: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    place_of_receipt: str = ""
    place_of_delivery: str = ""
    booking_reference: str = ""
    shipped_on_board_date: str = ""
    total_items: str = ""
    total_gross_weight: str = ""
    containers: List[ContainerDetail] = []
