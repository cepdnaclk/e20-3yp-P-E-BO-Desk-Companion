import java.util.*;

public class BraveryScore {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        int n = scanner.nextInt();
        scanner.nextLine();
        String[] names = scanner.nextLine().split(" ");
        int[] scores = new int[n];
        for (int i = 0; i < n; i++) {
            scores[i] = scanner.nextInt();
        }

        Arrays.sort(names);

        int[] sortedScores = scores.clone();
        Arrays.sort(sortedScores);

        List<String> bravest = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (scores[i] > 500) bravest.add(names[i]);
        }

        System.out.println(Arrays.toString(names));
        System.out.println(Arrays.toString(sortedScores));
        for (int i = 0; i < Math.min(5, bravest.size()); i++) {
            System.out.println(bravest.get(i));
        }
    }
}