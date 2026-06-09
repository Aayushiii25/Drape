from collectors.savana import SavanaCollector


class ProductService:

    def __init__(self):
        self.collector = SavanaCollector()

    def get_products_for_style(
        self,
        style: str,
        budget: int = None,
        color: str = None
    ):

        products = self.collector.search_products(
            goods_id=1859842
        )

        return products