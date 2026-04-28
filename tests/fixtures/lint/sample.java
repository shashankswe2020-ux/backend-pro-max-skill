import org.springframework.web.bind.annotation.*;

@RestController
public class OrderController {

    @PostMapping("/api/orders")
    public String createOrder(@RequestBody Map<String, Object> body) {
        // BPM-L005: Thread.sleep in controller
        Thread.sleep(1000);
        // BPM-L016: string format SQL
        String query = String.format("SELECT * FROM orders WHERE id = %s", body.get("id"));
        return "ok";
    }
}
