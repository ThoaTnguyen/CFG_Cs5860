// while, including a nested while. Logical condition as the header.
void whiles(int n) {
    int s = 0;
    int i = 0;
    while (i < n && s >= 0) {
        s = s + i;
        i = i + 1;
        while (s > 100) {
            s = s - 10;
        }
    }
    write(s);
}
