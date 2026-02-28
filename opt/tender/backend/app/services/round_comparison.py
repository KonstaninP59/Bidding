# app/services/round_comparison.py

async def compare_rounds(db, request_id, round1_id, round2_id):

    def build_offer_map(offers):
        data = {}
        for offer in offers:
            supplier_id = offer.invitation.supplier_id
            total = sum(i.line_total for i in offer.items)
            data[supplier_id] = {
                "total": total,
                "items": {
                    i.request_item_id: i.unit_price for i in offer.items
                }
            }
        return data

    result1 = await db.execute(
        select(Offer)
        .join(Invitation)
        .where(Invitation.round_id == round1_id)
    )

    result2 = await db.execute(
        select(Offer)
        .join(Invitation)
        .where(Invitation.round_id == round2_id)
    )

    offers1 = result1.scalars().unique().all()
    offers2 = result2.scalars().unique().all()

    map1 = build_offer_map(offers1)
    map2 = build_offer_map(offers2)

    comparison = []

    for supplier_id in set(map1.keys()) & set(map2.keys()):
        total1 = map1[supplier_id]["total"]
        total2 = map2[supplier_id]["total"]

        savings_abs = total1 - total2
        savings_pct = (savings_abs / total1 * 100) if total1 else 0

        comparison.append({
            "supplier_id": supplier_id,
            "round1_total": total1,
            "round2_total": total2,
            "savings_abs": savings_abs,
            "savings_pct": round(savings_pct, 2),
        })

    return comparison

# @router.get("/compare-rounds")
# async def compare(
#     request_id: int,
#     round1_id: int,
#     round2_id: int,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(require_permissions(["view_requests"])),
# ):
#     data = await compare_rounds(db, request_id, round1_id, round2_id)
#     return data