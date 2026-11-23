// A compound logical expression used as a condition AND as a value.
void logic(int a, int b) {
    boolean flag = a > 0 && b < 10;
    if (flag) {
        write(a);
    }
    if (a > 0 || b > 0) {
        write(b);
    }
}
