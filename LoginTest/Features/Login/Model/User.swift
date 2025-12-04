//
//  User.swift
//  LoginTest
//
//  Created by Manish.K on 11/28/25.
//

import Foundation

struct User: Identifiable, Codable {
    let id: UUID
    let name: String?
    let email: String?
}
