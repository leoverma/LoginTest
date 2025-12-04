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
    
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    func signup() async {
        guard validateFields() else {
            errorMessage = "Please check the form fields."
            return 
        }
        
        isLoading = true
        defer { isLoading = false }
        
        do {
            try await performSignup()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
    
    private func validateFields() -> Bool {
        // Add real validation
        true
    }
    
    private func performSignup() async throws {
        // API call goes here
        print("Signup click")
    }
}
