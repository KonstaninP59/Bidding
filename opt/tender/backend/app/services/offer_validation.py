async def validate_negotiation_rules(
    db,
    invitation,
    new_prices: dict[int, float],
):
    round_obj = invitation.round

    if round_obj.round_number == 1:
        return

    category = round_obj.request.category

    if not category.forbid_price_increase:
        return

    prev_round_number = round_obj.round_number - 1

    result = await db.execute(
        select(Offer)
        .join(Invitation)
        .join(Round)
        .where(
            Invitation.supplier_id == invitation.supplier_id,
            Round.round_number == prev_round_number,
            Round.request_id == round_obj.request_id,
        )
    )

    prev_offer = result.scalar_one_or_none()

    if not prev_offer:
        return

    prev_prices = {i.request_item_id: i.unit_price for i in prev_offer.items}

    for item_id, new_price in new_prices.items():
        if new_price > prev_prices.get(item_id, 0):
            raise HTTPException(
                400,
                f"Price increase forbidden for item {item_id}"
            )
