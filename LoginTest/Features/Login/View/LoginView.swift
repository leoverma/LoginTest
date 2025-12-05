//
//  LoginView.swift
//  LoginTest
//
//  Created by Manish.K on 11/29/25.
//

import SwiftUI

struct LoginView: View {
//    @StateObject private var viewModel = LoginViewModel(signupVM: SignupViewModel(), authService: AuthService())
    
    @StateObject var loginVM: LoginViewModel

    var body: some View {
        VStack(spacing: 16) {
            Text("Welcome back")
                .font(.title).bold()
            
            TextField("Email", text: $loginVM.email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .textFieldStyle(.roundedBorder)
            
            SecureField("Password", text: $loginVM.password)
                .textFieldStyle(.roundedBorder)
            
            if let message = loginVM.errorMessage {
                Text(message)
                    .foregroundColor(((loginVM.loggedInUser?.name) != nil) ?.green : .red)
                    .font(.footnote)
            }
            HStack{
            Button {
                loginVM.login()
            } label: {
                if loginVM.isLoading {
                    ProgressView()
                } else {
                    Text("Login")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(loginVM.isLoading)
            
            
            Button {
                Task {
                    await loginVM.signupVM.signup()
                }
            } label: {
                if loginVM.isLoading {
                    ProgressView()
                } else {
                    Text("Signup")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
        }
        }
        .padding()
    }
}

#Preview {
    let svm = SignupViewModel()
    LoginView(loginVM: LoginViewModel(signupVM: svm, authService: AuthService()))
}
