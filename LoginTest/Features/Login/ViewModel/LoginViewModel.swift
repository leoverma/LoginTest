//
//  LoginViewModel.swift
//  LoginTest
//
//  Created by Manish.K on 11/28/25.
//

//import Foundation
//import Combine
//
//@MainActor
//final class LoginViewModel: ObservableObject {
//
//    // Input
//    @Published var email: String = ""
//    @Published var password: String = ""
//
//    // Output
//    @Published var isLoading: Bool = false
//    @Published var errorMessage: String?
//    @Published var loggedInUser: User?
//
//    private let authService: AuthServicing
//
//    init(authService: AuthServicing ) {
//        self.authService = authService
//    }
//
//    func login() {
//        guard validate() else { return }
//
//        isLoading = true
//        Task {
//            do {
//                let request = LoginRequest(email: email, password: password)
//                let user = try await authService.login(request: request)
//                loggedInUser = user
//                errorMessage = "Welcome \(user.name.uppercased())!!!"
//            } catch {
//                errorMessage = "Login failed. Please try again."
//            }
//            isLoading = false
//        }
//    }
//
//    private func validate() -> Bool {
//        guard !email.isEmpty, !password.isEmpty else {
//            errorMessage = "Email and password are required."
//            return false
//        }
//        return true
//    }
//}


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
    
    // Optional: Add more detailed state tracking
    @Published var loginState: LoginState = .idle

    private let authService: AuthServicing

    init(authService: AuthServicing) {
        self.authService = authService
    }

    func login() {
        guard validate() else { return }

        isLoading = true
        loginState = .loading
        errorMessage = nil
        
        Task {
            do {
                let request = LoginRequest(email: email, password: password)
                let user = try await authService.login(request: request)
                
                // Set user first, then success message
                loggedInUser = user
                loginState = .success(user)
                errorMessage = "Welcome \(user.name.uppercased())!!!"
                
            } catch let authError as AuthError {
                // Handle specific auth errors
                handleAuthError(authError)
                
            } catch {
                // Handle generic errors
                handleGenericError(error)
            }
            
            isLoading = false
        }
    }
    
    private func handleAuthError(_ error: AuthError) {
        switch error {
        case .invalidCredentials:
            errorMessage = "Invalid email or password."
        case .networkError:
            errorMessage = "Network error. Please check your connection."
        case .serverError:
            errorMessage = "Server error. Please try again later."
        default:
            errorMessage = "Login failed. Please try again."
        }
        
        // Ensure loggedInUser is nil on failure
        loggedInUser = nil
        loginState = .error(error)
    }
    
    private func handleGenericError(_ error: Error) {
        errorMessage = "An unexpected error occurred. Please try again."
        loggedInUser = nil
        loginState = .error(error)
    }

    private func validate() -> Bool {
        // Clear previous state
        errorMessage = nil
        
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
    
    // Optional: Add a logout function to properly reset state
    func logout() {
        loggedInUser = nil
        errorMessage = nil
        loginState = .idle
        password = "" // Clear sensitive data
    }
    
    // Optional: Reset function for form
    func reset() {
        errorMessage = nil
        loginState = .idle
        // Don't clear email/password here to preserve user input
        // unless they explicitly cancel
    }
}

// Optional: State enum for better tracking
enum LoginState: Equatable {
    case idle
    case loading
    case success(User)
    case error(Error)
    
    static func == (lhs: LoginState, rhs: LoginState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle),
             (.loading, .loading):
            return true
        case (.success(let lhsUser), .success(let rhsUser)):
            return lhsUser.id == rhsUser.id
        case (.error(let lhsError), .error(let rhsError)):
            return lhsError.localizedDescription == rhsError.localizedDescription
        default:
            return false
        }
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


// If your auth service doesn't have AuthError, define it or remove the check
enum AuthError: Error, LocalizedError {
    case invalidCredentials
    case networkError
    case serverError
    case userNotFound
    case accountLocked
    case unknownError
    
    var errorDescription: String? {
        switch self {
        case .invalidCredentials:
            return "Invalid credentials"
        case .networkError:
            return "Network error"
        case .serverError:
            return "Server error"
        case .userNotFound:
            return "User not found"
        case .accountLocked:
            return "Account locked"
        case .unknownError:
            return "Unknown error occurred"
        }
    }
}
