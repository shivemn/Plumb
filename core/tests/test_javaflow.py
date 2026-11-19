from __future__ import annotations

from collections.abc import Callable

from plumb.entrypoints import find_entry_points
from plumb.flow import trace_flows
from plumb.inventory import build_inventory
from tests.conftest import RepoBuilder

Make = Callable[[str], RepoBuilder]
BASE = "src/main/java/com/shop/"

CONTROLLER = """package com.shop;

@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderService orders;

    public OrderController(OrderService orders) { this.orders = orders; }

    @GetMapping("/{id}")
    public Order get(@PathVariable long id) {
        return this.orders.find(id);
    }

    @PostMapping
    public Order place(@RequestBody Order order) {
        Order saved = orders.place(order);
        order.getId();
        return saved;
    }
}
"""

SERVICE = """package com.shop;
public interface OrderService {
    Order find(long id);
    Order place(Order order);
}
"""

SERVICE_IMPL = """package com.shop;
@Service
public class OrderServiceImpl implements OrderService {
    private final OrderRepository repository;
    private final RestTemplate rest;

    public Order find(long id) { return repository.findById(id).orElseThrow(); }

    public Order place(Order order) {
        check(order);
        rest.postForObject("http://billing", order, Void.class);
        return repository.save(order);
    }

    private void check(Order order) { if (order == null) throw new IllegalArgumentException(); }
}
"""

REPOSITORY = """package com.shop;
public interface OrderRepository extends JpaRepository<Order, Long> {}
"""

ORDER = """package com.shop;
public class Order {
    private long id;
    public long getId() { return id; }
}
"""


def test_spring_trace_through_interface_to_repository(make_repo: Make) -> None:
    repo = make_repo("repo")
    repo.run("init", "-q")
    repo.commit(
        {
            BASE + "OrderController.java": CONTROLLER,
            BASE + "OrderService.java": SERVICE,
            BASE + "OrderServiceImpl.java": SERVICE_IMPL,
            BASE + "OrderRepository.java": REPOSITORY,
            BASE + "Order.java": ORDER,
        }
    )
    files = build_inventory(repo.path)
    flows = trace_flows(repo.path, files, find_entry_points(repo.path, files))
    by_route = {f.route.name: f for f in flows}

    get = by_route["GET /orders/{id}"]
    assert [s.name for s in get.steps] == ["OrderController.get", "OrderServiceImpl.find"]
    assert [(t.what, t.call) for t in get.touches] == [("the database", "repository.findById")]

    place = by_route["POST /orders"]
    assert [s.name for s in place.steps] == [
        "OrderController.place",
        "OrderServiceImpl.place",
        "OrderServiceImpl.check",
    ]  # Order.getId is a getter, so it is not a step
    assert [t.what for t in place.touches] == ["an outside HTTP service", "the database"]
    assert place.steps[1].path == BASE + "OrderServiceImpl.java"
