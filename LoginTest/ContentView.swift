//
//  ContentView.swift
//  LoginTest
//
//  Created by Manish.K on 11/28/25.
//

import SwiftUI

struct ContentView: View {
    var body: some View {
        LoginView(loginVM: LoginViewModel(signupVM: SignupViewModel(), authService: AuthService()))
            .padding(0)
    }
}

#Preview {
    ContentView()
}
