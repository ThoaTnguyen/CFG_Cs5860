// Extra credit: break and continue inside while / for.
void loopControl(int n) {
    int s = 0;
    int i = 0;
    while (i < n) {
        i = i + 1;
        if (i == 2) {
            continue;
        }
        if (i == 8) {
            break;
        }
        s = s + i;
    }
    for (int j = 0; j < n; j = j + 1) {
        if (j == 3) {
            break;
        }
        s = s + j;
    }
    write(s);
}
