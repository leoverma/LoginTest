//
//  AuthService.swift
//  LoginTest
//
//  Created by Manish.K on 11/28/25.
//

import Foundation

protocol AuthServicing {
    func login(request: LoginRequest) async throws -> User
}

final class AuthService: AuthServicing {
    func login(request: LoginRequest) async throws -> User {
        // Call API here (URLSession / Alamofire etc.)
        // Map response to User and return
//        throw NSError(domain: "NotImplemented", code: -1)
        let domain = request.email.lowercased().split(separator: "@")[1]
        // print(domain)
        if domain == "gmail.com"{
            let user = User(id: "1", name: String(request.email.lowercased().split(separator: "@")[0]), email: request.email.lowercased())
            return user
        }
        throw NSError(domain: "NotImplemented", code: -1)
    }
}
