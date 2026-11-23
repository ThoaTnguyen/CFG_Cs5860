// Extra credit: ?: , ++/--, Java 5 for-each, calls of other functions.
void extras(int n, int[] arr) {
    int x = 0;
    x = n > 0 ? n : -n;
    x++;
    --x;
    foo(x);
    bar(x + 1, n);
    for (int v : arr) {
        write(v);
    }
}
