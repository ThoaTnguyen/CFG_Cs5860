// Extra credit: switch (with fall-through) and return.
int classify(int x) {
    int kind = 0;
    switch (x) {
        case 0:
            kind = 0;
            break;
        case 1:
        case 2:
            kind = 1;
            break;
        case 3:
            kind = 2;
            // fall through
        default:
            kind = kind + 10;
            return kind;
    }
    write(kind);
    exit(0);
}
