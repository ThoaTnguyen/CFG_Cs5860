// Sequential assignments, arithmetic, read/write, comments.
// Comments must not become vertices and must not split a block.
void straight() {
    int a = 1;          // comment between statements
    int b = a + 2 * 3;
    int c = 0;
    read(c);
    /* block comment */
    write(b);
    c = b - a;
}
