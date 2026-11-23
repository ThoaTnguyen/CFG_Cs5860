// Classic for. Init / condition / update / body, nested for.
void fors(int n) {
    int s = 0;
    for (int i = 0; i < n && s >= 0; i = i + 1) {
        for (int j = 0; j < i; j = j + 1) {
            s = s + i * j;
        }
    }
    write(s);
}
