//
//  SignupViewModel.swift
//  LoginTest
//
//  Created by Manish.K on 12/4/25.
//

import Foundation
import Combine

@MainActor
final class SignupViewModel: ObservableObject {
    
    @Published var email: String = ""
    @Published var password: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var signupSuccess: Bool = false

    func signup() async {
        // 1. Validate form inputs
        guard validateFields() else { return }
        
        // 2. Start loading
        isLoading = true
        errorMessage = nil
        
        do {
            // 3. Perform signup call
            try await performSignup()
            signupSuccess = true
            
        } catch {
            errorMessage = error.localizedDescription
        }
        
        // 4. Stop loading
        isLoading = false
    }

    // MARK: - Validation
    private func validateFields() -> Bool {
        if email.isEmpty {
            errorMessage = "Email cannot be empty."
            return false
        }
        
        if !email.contains("@") {
            errorMessage = "Please enter a valid email."
            return false
        }
        
        if password.count < 6 {
            errorMessage = "Password must be at least 6 characters."
            return false
        }
        
        return true
    }

    // MARK: - API Call (Mock)
    private func performSignup() async throws {
        // Simulate network delay
        try await Task.sleep(for: .seconds(1))

        // Simulate success or failure
        let success = Bool.random()
        
        if !success {
            throw SignupError.failed
        }
    }

    enum SignupError: LocalizedError {
        case failed
        
        var errorDescription: String? {
            switch self {
            case .failed:
                return "Signup failed. Please try again."
            }
        }
    }
}
