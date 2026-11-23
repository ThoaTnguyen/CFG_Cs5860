// A class wrapper is accepted; each method gets its own graph.
public class Sample {
    public static void main(int n) {
        int s = 0;
        for (int i = 0; i < n; i++) {
            s += i;
        }
        write(s);
        return;
    }
}
