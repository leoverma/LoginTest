//
//  LoginView.swift
//  LoginTest
//
//  Created by Manish.K on 11/29/25.
//

import SwiftUI

struct LoginView: View {
    @StateObject private var viewModel = LoginViewModel(authService: AuthService())

    var body: some View {
        VStack(spacing: 16) {
            Text("Welcome back")
                .font(.title).bold()
            
            TextField("Email", text: $viewModel.email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .textFieldStyle(.roundedBorder)
            
            SecureField("Password", text: $viewModel.password)
                .textFieldStyle(.roundedBorder)
            
            if let message = viewModel.errorMessage {
                Text(message)
                    .foregroundColor(((viewModel.loggedInUser?.name) != nil) ?.green : .red)
                    .font(.footnote)
            }
            HStack{
            Button {
                viewModel.login()
            } label: {
                if viewModel.isLoading {
                    ProgressView()
                } else {
                    Text("Login")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading)
            
            
            Button {
                viewModel.signupVM.signup()
            } label: {
                if viewModel.isLoading {
                    ProgressView()
                } else {
                    Text("Signup")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading)
        }
        }
        .padding()
    }
}

#Preview {
    LoginView()
}
