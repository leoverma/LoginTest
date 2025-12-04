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
                    .foregroundColor(((viewModel.loggedInUser) != nil) ?.green : .red)
                    .font(.footnote)
            }

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
            .padding()
            
            
            switch viewModel.loginState {
                case .loading:
                    ProgressView()
                case .success(let user):
                    Text("Welcome \(user.name)!")
                        .foregroundColor(.green)
                case .error(let error):
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                case .idle:
                    if let error = viewModel.errorMessage {
                        Text(error)
                            .foregroundColor(.red)
                    }
            }
        }
        
    }
}

#Preview {
    LoginView()
}
