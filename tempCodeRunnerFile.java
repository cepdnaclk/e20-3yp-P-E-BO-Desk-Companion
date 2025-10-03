import org.junit.Test;
import static org.junit.Assert.*;

public class CalculatorTest {
    private Calculator calc = new Calculator();

    @Test
    public void testAdd() {
        assertEquals(5, calc.add(2, 3));
        assertEquals(0, calc.add(-1, 1));
    }

    @Test
    public void testSubtract() {
        assertEquals(2, calc.subtract(5, 3));
        assertEquals(-4, calc.subtract(1, 5));
    }

    @Test
    public void testMultiply() {
        assertEquals(6, calc.multiply(2, 3));
        assertEquals(0, calc.multiply(5, 0));
    }

    @Test
    public void testDivide() {
        assertEquals(2, calc.divide(6, 3));
        assertEquals(5, calc.divide(10, 2));
    }
}