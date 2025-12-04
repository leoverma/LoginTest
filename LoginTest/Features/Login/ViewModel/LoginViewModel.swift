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

    init(authService: AuthService){
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
                loggedInUser = User(id: UUID(), name: nil, email: nil)
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
        return true
    }
}
