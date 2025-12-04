//
//  LoginViewModel.swift
//  LoginTest
//
//  Created by Manish.K on 11/28/25.
//

import Foundation
import Combine

@MainActor
final class LoginViewModel: ObservableObject {

    // Input
    @Published var email: String = ""
    @Published var password: String = ""

    // Output
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var loggedInUser: User?

    private let authService: AuthServicing

    init(authService: AuthServicing = AuthService()) {
        self.authService = authService
    }

    func login() {
        errorMessage = nil
        guard validate() else { return }

        isLoading = true
        Task {
            do {
                let request = LoginRequest(email: email, password: password)
                let user = try await authService.login(request: request)
                loggedInUser = user
                errorMessage = "Welcome \(user.name?.uppercased() ?? "")!!!"
            } catch {
                loggedInUser = User(id: "0", name: nil, email: nil)
                errorMessage = "Login failed. Please try again."
            }
            isLoading = false
        }
    }

    private func validate() -> Bool {
        guard !email.isEmpty, !password.isEmpty else {
            errorMessage = "Email and password are required."
            return false
        }
        guard email.isValidEmail else {
            errorMessage = "Please enter a valid email address."
            return false
        }
        
        guard password.count >= 6 else {
            errorMessage = "Password must be at least 6 characters."
            return false
        }
        return true
    }
}

// Email validation extension
extension String {
    var isValidEmail: Bool {
        let emailRegEx = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPredicate = NSPredicate(format:"SELF MATCHES %@", emailRegEx)
        return emailPredicate.evaluate(with: self)
    }
}
