// if-then, if-else, nested if, compound condition of two predicates.
void ifs(int x, int y) {
    int a = 0;
    if (x > 0) {
        a = 1;
    }
    if (x > 0 && y < 10) {
        a = 2;
    } else {
        a = 3;
    }
    if (x > 0) {
        if (y > 0) {
            a = 4;
        } else {
            a = 5;
        }
    }
    write(a);
}
