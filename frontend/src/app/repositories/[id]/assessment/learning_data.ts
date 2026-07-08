export interface ConceptDetails {
  title: string;
  definition: string;
  badExample: string;
  goodExample: string;
  whyIndustryUsesIt: string;
  recommendedReading: string[];
}

export const LEARNING_DATA: Record<string, ConceptDetails> = {
  complexity: {
    title: "Cyclomatic Complexity",
    definition: "A quantitative measure of the number of linearly independent paths through a program's source code, calculated by counting decision points (ifs, loops, switch cases, logical operators).",
    badExample: `// Bad: High Cyclomatic Complexity
public void processTransaction(Transaction t) {
    if (t != null) {
        if (t.getStatus() == Status.PENDING) {
            if (t.getAmount() > 1000) {
                if (t.isRiskFlagged()) {
                    reject(t);
                } else {
                    approveWithReview(t);
                }
            } else {
                approveDirectly(t);
            }
        } else if (t.getStatus() == Status.ACTIVE) {
            // More nested logic...
        }
    }
}`,
    goodExample: `// Good: Low Cyclomatic Complexity (Polymorphism / Guard Clauses)
public void processTransaction(Transaction t) {
    if (t == null || t.getStatus() != Status.PENDING) return;
    if (t.getAmount() <= 1000) {
        approveDirectly(t);
        return;
    }
    if (t.isRiskFlagged()) {
        reject(t);
        return;
    }
    approveWithReview(t);
}`,
    whyIndustryUsesIt: "Google, Microsoft, and Amazon enforce strict complexity limits (typically max 10-15 per function) to ensure code remains unit-testable and simple for peer reviews. Code with high complexity exhibits exponential risk of regression defects.",
    recommendedReading: [
      "Martin Fowler - Refactoring (2nd Edition)",
      "Steve McConnell - Code Complete",
      "Refactoring.Guru - Simplifying Conditional Expressions"
    ]
  },
  srp: {
    title: "Single Responsibility Principle (SRP)",
    definition: "The Single Responsibility Principle states that a class should have one, and only one, reason to change.",
    badExample: `// Bad: God Class violating SRP
public class UserManager {
    public void createUser(User u) { /* db insert */ }
    public void sendEmail(String msg) { /* SMTP logic */ }
    public void exportReportJSON(User u) { /* JSON serializer */ }
}`,
    goodExample: `// Good: Classes divided by single concern
public class UserRepository {
    public void saveUser(User u) { /* DB insertion */ }
}
public class NotificationService {
    public void sendEmail(String msg) { /* SMTP dispatcher */ }
}
public class UserReportSerializer {
    public String toJson(User u) { /* JSON converter */ }
}`,
    whyIndustryUsesIt: "Applying SRP decouples classes. Amazon utilizes SRP to ensure distinct microservices can change and scale independently without breaking concurrent modules.",
    recommendedReading: [
      "Robert C. Martin - Clean Architecture",
      "Uncle Bob - SOLID Principles Explained",
      "Martin Fowler - Refactoring: Split Class"
    ]
  },
  dip: {
    title: "Dependency Inversion Principle (DIP)",
    definition: "High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details; details should depend on abstractions.",
    badExample: `// Bad: Tight coupling on concrete low-level implementation
public class OrderService {
    private MySQLDatabase database = new MySQLDatabase(); // concrete
    public void save() { database.insert(); }
}`,
    goodExample: `// Good: Depend on interface abstractions
public class OrderService {
    private Database database; // abstract interface
    public OrderService(Database db) { this.database = db; } // injected
    public void save() { database.insert(); }
}`,
    whyIndustryUsesIt: "DIP enables dependency injection (Spring Boot / NestJS). This allows mock implementations to be swapped in during automated unit testing without spinning up live databases.",
    recommendedReading: [
      "Uncle Bob - Agile Software Development, Principles, Patterns, and Practices",
      "Dependency Injection in .NET / Java",
      "Martin Fowler - Inversion of Control Containers and the Dependency Injection Pattern"
    ]
  },
  dry: {
    title: "DRY (Don't Repeat Yourself)",
    definition: "Every piece of system logic must have a single, unambiguous representation within the codebase. Duplicate code increases maintenance overhead and spreads bugs.",
    badExample: `// Bad: Duplicated parsing and validation checks
public void validateUser(User u) {
    if (u.getEmail() == null || !u.getEmail().contains("@")) throw new IllegalArgumentException();
}
public void validateAdmin(Admin a) {
    if (a.getEmail() == null || !a.getEmail().contains("@")) throw new IllegalArgumentException();
}`,
    goodExample: `// Good: Shared validator logic helper
public class EmailValidator {
    public static void validate(String email) {
        if (email == null || !email.contains("@")) throw new IllegalArgumentException();
    }
}`,
    whyIndustryUsesIt: "Duplicate logic wastes development time. Industry leaders enforce strict sonar checks (e.g. SonarQube, CodeQL) to flag duplicated chunks, keeping systems DRY and coherent.",
    recommendedReading: [
      "Andrew Hunt & David Thomas - The Pragmatic Programmer",
      "Refactoring.Guru - Extract Method",
      "Martin Fowler - Refactoring: Pull Up Method"
    ]
  },
  coupling: {
    title: "Low Coupling & High Cohesion",
    definition: "Coupling refers to how closely connected modules are. Cohesion refers to how focused a single module's responsibilities are. You should strive for low coupling and high cohesion.",
    badExample: `// Bad: High Coupling (direct field references on other classes)
public class Invoice {
    public double calculateTotal(Order order) {
        return order.items.get(0).price * order.quantity + order.shipping.cost;
    }
}`,
    goodExample: `// Good: Low Coupling (delegated behavior / Tell Don't Ask)
public class Invoice {
    public double calculateTotal(Order order) {
        return order.getTotalPrice() + order.getShippingCost();
    }
}`,
    whyIndustryUsesIt: "Highly coupled systems suffer from 'cascading breakages' where a minor change in a database schema breaks compilation across dozens of unrelated UI controllers.",
    recommendedReading: [
      "Steve McConnell - Code Complete (Chapter 5: Design in Construction)",
      "Clean Code - Chapter 6: Objects and Data Structures",
      "Refactoring.Guru - Coupling smells"
    ]
  }
};
