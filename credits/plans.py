from dataclasses import dataclass


@dataclass(frozen=True)
class CreditPlan:
    code: str
    name: str
    credits: int
    price_usd: float
    description: str
    highlighted: bool = False
    badge: str = ""
    sort_order: int = 0

    @property
    def credits_per_usd(self):
        if not self.price_usd:
            return 0

        return round(
            self.credits / self.price_usd,
            1,
        )


# Single source of truth for Gingao credit packages.
# Edit these values to adjust:
# - price
# - credits
# - description
# - badge
# - display order
# - highlighted plan

PLANS = {

    "starter": CreditPlan(
        code="starter",
        name="Starter",
        credits=1200,
        price_usd=15.90,
        description=(
            "Para empezar a crear contenido "
            "con Gingao."
        ),
        sort_order=10,
    ),

    "creator": CreditPlan(
        code="creator",
        name="Creator",
        credits=2500,
        price_usd=29.90,
        description=(
            "Para creadores que publican "
            "contenido con frecuencia."
        ),
        highlighted=True,
        badge="M\u00e1s popular",
        sort_order=20,
    ),

    "plus": CreditPlan(
        code="plus",
        name="Plus",
        credits=4500,
        price_usd=49.90,
        description=(
            "M\u00e1s capacidad para proyectos "
            "y publicaciones regulares."
        ),
        sort_order=30,
    ),

    "pro": CreditPlan(
        code="pro",
        name="Pro",
        credits=9500,
        price_usd=99.90,
        description=(
            "Para producci\u00f3n continua "
            "y mayor volumen."
        ),
        sort_order=40,
    ),

    "studio": CreditPlan(
        code="studio",
        name="Studio",
        credits=20000,
        price_usd=199.90,
        description=(
            "Pensado para estudios, equipos "
            "y producci\u00f3n intensiva."
        ),
        sort_order=50,
    ),

    "business": CreditPlan(
        code="business",
        name="Business",
        credits=42000,
        price_usd=399.90,
        description=(
            "M\u00e1ximo volumen y mejor coste "
            "por cr\u00e9dito."
        ),
        badge="Mejor valor",
        sort_order=60,
    ),
}


def get_plan(code):
    return PLANS.get(
        str(code or "")
        .strip()
        .lower()
    )


def all_plans():
    return sorted(
        PLANS.values(),
        key=lambda plan: (
            plan.sort_order,
            plan.price_usd,
        ),
    )
