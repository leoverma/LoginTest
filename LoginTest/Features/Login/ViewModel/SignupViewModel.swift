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
    
    // MARK: - Input Fields
    @Published var email: String = ""
    @Published var password: String = ""
    
    // MARK: - UI State
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var signupSuccess: Bool = false

    // MARK: - Public API
    /// Triggers the signup process with validation, async work, and error handling.
    func signup() async {
        errorMessage = nil
        signupSuccess = false
        
        guard validateFields() else { return }
        
        isLoading = true
        
        do {
            try await performSignup()
            signupSuccess = true
            errorMessage = nil    // Clear any old errors
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }

    // MARK: - Validation
    /// Validates email and password with realistic edge cases.
    private func validateFields() -> Bool {
        
        if email.trimmingCharacters(in: .whitespaces).isEmpty {
            errorMessage = "Email cannot be empty."
            return false
        }
        
        if !email.contains("@") || !email.contains(".") {
            errorMessage = "Invalid email format."
            return false
        }
        
        if password.count < 8 {
            errorMessage = "Password must be at least 8 characters long."
            return false
        }
        
        if password.lowercased().contains("password") {
            errorMessage = "Password cannot contain the word 'password'."
            return false
        }

        return true
    }

    // MARK: - "API" Layer (Mock)
    /// Simulates a network signup request. Replace with real API later.
    private func performSignup() async throws {
        
        // Simulate internet delay
        try await Task.sleep(for: .seconds(1))
        
        // Example: 20% failure rate for realism
        if Bool.random() == false {
            throw SignupError.serverUnavailable
        }
    }
    
    enum SignupError: LocalizedError {
        case serverUnavailable
        
        var errorDescription: String? {
            switch self {
            case .serverUnavailable:
                return "Server is currently unavailable. Please try again."
            }
        }
    }
}

