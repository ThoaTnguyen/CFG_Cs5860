// Required constructs nested at several depths, plus a logical assignment.
void nested(int n) {
    int s = 0;
    boolean ok = n > 0 && n < 1000;
    if (ok) {
        int i = 0;
        while (i < n) {
            for (int j = 0; j < i; j = j + 1) {
                if (j % 2 == 0) {
                    s = s + j;
                } else {
                    s = s - 1;
                }
            }
            do {
                i = i + 1;
            } while (i % 3 == 0);
        }
    } else {
        read(s);
    }
    write(s);
}
