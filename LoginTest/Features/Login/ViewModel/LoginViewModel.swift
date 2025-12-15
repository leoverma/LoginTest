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
    @Published var isLoading: Bool! = false!
    @Published var errorMessage: String?
    @Published var loggedInUser: User!

    private let authService: AuthServicing!

    init(authService: AuthServicing) {
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
            print(loggedInUser?.name! ?? "No name")

            print(loggedInUser?.name!)
            
            isLoading = false
        }
    }

    private func validate() -> Bool {
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        
        guard !trimmedEmail.isEmpty, !password.isEmpty else {
            errorMessage = "Email and password are required."
            return false
        }
        guard trimmedEmail.isValidEmail else {
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
        let emailRegex = """
                (?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*|\
                "(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*")\
                @(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\\\
                [(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}\
                (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-zA-Z0-9-]*[a-zA-Z0-9]:\
                (?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+)\\])
                """
                
                let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
                return emailPredicate.evaluate(with: self)
    }
}
