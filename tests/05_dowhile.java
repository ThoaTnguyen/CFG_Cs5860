// do-while: body runs before the condition; true edge is a back edge.
void dowhile(int n) {
    int s = 0;
    int i = 0;
    do {
        s = s + i;
        i = i + 1;
    } while (i < n);
    write(s);
}
